#include "scrapers/ExternalScraper.h"
#include "FileData.h"
#include "Log.h"
#include "Settings.h"
#include "SystemData.h"
#include "utils/FileSystemUtil.h"
#include "utils/StringUtil.h"

#include <cstdio>
#include <rapidjson/document.h>

using namespace rapidjson;

static std::string shellQuote(const std::string& s)
{
	return "'" + Utils::String::replace(s, "'", "'\\''") + "'";
}

void ExternalScraper::generateRequests(const ScraperSearchParams& params, std::queue<std::unique_ptr<ScraperRequest>>& requests, std::vector<ScraperSearchResult>& results)
{
	if (params.game == nullptr || params.system == nullptr)
		return;

	std::string name = params.nameOverride.empty() ? params.game->getName() : params.nameOverride;

	std::string cmd = "acrobato-scrape " + mSource +
		" --system " + shellQuote(params.system->getName()) +
		" --file " + shellQuote(params.game->getPath()) +
		" --name " + shellQuote(name) +
		(params.isManualScrape ? " --manual" : "") + " 2>/dev/null";

	std::string scraperName = Scraper::getScraperName(this);
	requests.push(std::unique_ptr<ScraperRequest>(new ExternalScraperRequest(results, scraperName, cmd)));
}

ExternalScraperRequest::ExternalScraperRequest(std::vector<ScraperSearchResult>& resultsWrite, const std::string& scraperName, const std::string& command)
	: ScraperRequest(resultsWrite), mScraperName(scraperName), mDone(false)
{
	mThread = std::thread([this, command]
	{
		std::string out;
		FILE* pipe = popen(command.c_str(), "r");
		if (pipe != nullptr)
		{
			char buf[4096];
			size_t n;
			while ((n = fread(buf, 1, sizeof(buf), pipe)) > 0)
				out.append(buf, n);
			pclose(pipe);
		}
		mOutput = out;
		mDone = true;
	});
}

ExternalScraperRequest::~ExternalScraperRequest()
{
	if (mThread.joinable())
		mThread.join();
}

static std::string str(const Value& o, const char* key)
{
	return (o.HasMember(key) && o[key].IsString()) ? o[key].GetString() : "";
}

void ExternalScraperRequest::update()
{
	if (!mDone)
		return;

	if (mThread.joinable())
		mThread.join();

	setStatus(ASYNC_DONE);

	Document doc;
	doc.Parse(mOutput.c_str());
	if (doc.HasParseError() || !doc.IsArray())
	{
		std::string err = (!doc.HasParseError() && doc.IsObject()) ? str(doc, "error") : "no response";
		LOG(LogError) << mScraperName << ": " << err;
		return; // no results; never throw (an uncaught exception closes ES)
	}

	for (auto& r : doc.GetArray())
	{
		if (!r.IsObject() || str(r, "name").empty())
			continue;

		ScraperSearchResult result(mScraperName);
		result.mdl.set(MetaDataId::Name, str(r, "name"));

		std::string desc = str(r, "desc");
		if (!desc.empty())
			result.mdl.set(MetaDataId::Desc, desc);

		std::string date = str(r, "releasedate");
		if (date.size() == 8)
			result.mdl.set(MetaDataId::ReleaseDate, date + "T000000");
		else if (date.size() == 4)
			result.mdl.set(MetaDataId::ReleaseDate, date + "0101T000000");

		for (auto field : { std::make_pair("developer", MetaDataId::Developer), std::make_pair("publisher", MetaDataId::Publisher),
			                std::make_pair("genre", MetaDataId::Genre), std::make_pair("players", MetaDataId::Players) })
		{
			std::string v = str(r, field.first);
			if (!v.empty())
				result.mdl.set(field.second, v);
		}

		std::string rating = str(r, "rating");
		result.mdl.set(MetaDataId::Rating, (!rating.empty() && Settings::getInstance()->getBool("ScrapeRatings")) ? rating : "-1");

		std::map<std::string, std::string> media;
		if (r.HasMember("media") && r["media"].IsObject())
			for (auto& m : r["media"].GetObject())
				if (m.value.IsString())
					media[m.name.GetString()] = m.value.GetString();

		applyScrapedMedia(result, media);
		mResults.push_back(result);
	}
}

static ScraperSearchItem mediaItem(const std::string& url)
{
	std::string ext = Utils::String::toLower(Utils::FileSystem::getExtension(Utils::String::split(url, '?')[0]));
	if (ext != ".png" && ext != ".jpg" && ext != ".jpeg")
		ext = ".png";
	return ScraperSearchItem(url, ext);
}

static std::string pick(const std::map<std::string, std::string>& media, std::initializer_list<const char*> keys)
{
	for (auto k : keys)
	{
		auto it = media.find(k);
		if (it != media.cend() && !it->second.empty())
			return it->second;
	}
	return "";
}

void applyScrapedMedia(ScraperSearchResult& result, const std::map<std::string, std::string>& media)
{
	auto settings = Settings::getInstance();
	std::string imageSrc = settings->getString("ScrapperImageSrc");
	std::string thumbSrc = settings->getString("ScrapperThumbSrc");
	std::string logoSrc = settings->getString("ScrapperLogoSrc");

	std::string image;
	if (imageSrc == "sstitle")
		image = pick(media, { "titleshot", "screenshot", "box2d" });
	else if (imageSrc == "box-2D")
		image = pick(media, { "box2d", "box3d" });
	else if (imageSrc == "box-3D")
		image = pick(media, { "box3d", "box2d" });
	else if (imageSrc == "fanart")
		image = pick(media, { "fanart", "screenshot", "box2d" });
	else if (!imageSrc.empty())
		image = pick(media, { "screenshot", "titleshot", "box2d" });
	if (!image.empty())
		result.urls[MetaDataId::Image] = mediaItem(image);

	std::string thumb;
	if (thumbSrc == "box-2D")
		thumb = pick(media, { "box2d", "box3d" });
	else if (thumbSrc == "box-3D")
		thumb = pick(media, { "box3d", "box2d" });
	if (!thumb.empty())
		result.urls[MetaDataId::Thumbnail] = mediaItem(thumb);

	std::string logo = pick(media, { "logo" });
	if (!logo.empty() && !logoSrc.empty())
		result.urls[MetaDataId::Marquee] = mediaItem(logo);

	std::string fanart = pick(media, { "fanart" });
	if (!fanart.empty() && settings->getBool("ScrapeFanart"))
		result.urls[MetaDataId::FanArt] = mediaItem(fanart);

	std::string back = pick(media, { "boxback" });
	if (!back.empty() && settings->getBool("ScrapeBoxBack"))
		result.urls[MetaDataId::BoxBack] = mediaItem(back);

	std::string title = pick(media, { "titleshot" });
	if (!title.empty())
		result.urls[MetaDataId::TitleShot] = mediaItem(title);

	std::string cart = pick(media, { "cartridge" });
	if (!cart.empty())
		result.urls[MetaDataId::Cartridge] = mediaItem(cart);
}
