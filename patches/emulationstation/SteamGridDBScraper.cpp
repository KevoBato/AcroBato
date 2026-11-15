#include "scrapers/SteamGridDBScraper.h"
#include "FileData.h"
#include "HttpReq.h"
#include "Log.h"
#include "Settings.h"
#include "SystemData.h"
#include "utils/FileSystemUtil.h"
#include "utils/StringUtil.h"
#include "utils/TimeUtil.h"

#include <rapidjson/document.h>
#include <rapidjson/error/en.h>

using namespace rapidjson;

static const std::string API = "https://www.steamgriddb.com/api/v2";

bool SteamGridDBScraper::hasApiKey()
{
	return !Utils::String::trim(Settings::getInstance()->getString("SteamGridDBApiKey")).empty();
}

const std::set<Scraper::ScraperMediaSource>& SteamGridDBScraper::getSupportedMedias()
{
	static std::set<ScraperMediaSource> mdds =
	{
		ScraperMediaSource::Box2d,     // grids (600x900 covers)
		ScraperMediaSource::FanArt,    // heroes
		ScraperMediaSource::Marquee,   // logos
		ScraperMediaSource::Wheel      // logos
	};

	return mdds;
}

static HttpReqOptions authOptions()
{
	HttpReqOptions options;
	options.customHeaders.push_back("Authorization: Bearer " + Utils::String::trim(Settings::getInstance()->getString("SteamGridDBApiKey")));
	options.customHeaders.push_back("Accept: application/json");
	return options;
}

void SteamGridDBScraper::generateRequests(const ScraperSearchParams& params, std::queue<std::unique_ptr<ScraperRequest>>& requests, std::vector<ScraperSearchResult>& results)
{
	// No exceptions here: an uncaught one closes ES (that was the scrape crash).
	if (!hasApiKey())
	{
		LOG(LogError) << "SteamGridDB: no API key set (Scraper > Accounts)";
		return;
	}

	std::string name = params.nameOverride;
	if (name.empty())
		name = Utils::String::removeParenthesis(params.game->getName());
	if (name.empty())
		name = Utils::String::removeParenthesis(Utils::FileSystem::getStem(params.game->getPath()));

	name = Utils::String::trim(name);
	if (name.empty())
		return;

	HttpReqOptions options = authOptions();
	std::string url = API + "/search/autocomplete/" + HttpReq::urlEncode(name);
	requests.push(std::unique_ptr<ScraperRequest>(new SteamGridDBSearchRequest(requests, results, url, &options, params.isManualScrape)));
}

static bool parseData(const std::string& response, Document& doc)
{
	doc.Parse(response.c_str());
	if (doc.HasParseError())
	{
		LOG(LogError) << "SteamGridDB: bad JSON: " << GetParseError_En(doc.GetParseError());
		return false;
	}

	if (!doc.IsObject() || !doc.HasMember("success") || !doc["success"].IsBool() || !doc["success"].GetBool() || !doc.HasMember("data"))
	{
		if (doc.IsObject() && doc.HasMember("errors"))
			LOG(LogError) << "SteamGridDB: request refused (check the API key)";
		return false;
	}

	return true;
}

bool SteamGridDBSearchRequest::process(const std::string& response, std::vector<ScraperSearchResult>& results)
{
	Document doc;
	if (!parseData(response, doc) || !doc["data"].IsArray())
	{
		setError("SteamGridDB: search failed (check the API key in Scraper > Accounts)");
		return true;
	}

	const Value& games = doc["data"];
	int max = mIsManualScrape ? 6 : 1; // automatic scraping takes the best match
	for (int i = 0; i < (int)games.Size() && i < max; i++)
	{
		const Value& game = games[i];
		if (!game.HasMember("id") || !game["id"].IsInt() || !game.HasMember("name") || !game["name"].IsString())
			continue;

		std::string year;
		if (game.HasMember("release_date") && game["release_date"].IsInt64() && game["release_date"].GetInt64() > 0)
			year = Utils::Time::timeToString((time_t)game["release_date"].GetInt64(), "%Y");

		mRequestQueue->push(std::unique_ptr<ScraperRequest>(
			new SteamGridDBGameRequest(results, game["id"].GetInt(), game["name"].GetString(), year, &mOptions, mIsManualScrape)));
	}

	return true;
}

SteamGridDBGameRequest::SteamGridDBGameRequest(std::vector<ScraperSearchResult>& resultsWrite, int gameId, const std::string& name,
	const std::string& year, HttpReqOptions* options, bool isManualScrape)
	: ScraperHttpRequest(resultsWrite, API + "/grids/game/" + std::to_string(gameId) + "?dimensions=600x900,342x482,660x930&types=static&mimes=image/png,image/jpeg", options),
	  mName(name), mYear(year), mIsManualScrape(isManualScrape)
{
	std::string id = std::to_string(gameId);
	mDependencyQueue.push(std::pair<std::string, std::string>("heroes", API + "/heroes/game/" + id + "?types=static&mimes=image/png,image/jpeg"));
	mDependencyQueue.push(std::pair<std::string, std::string>("logos", API + "/logos/game/" + id + "?types=static&mimes=image/png"));
}

static std::string firstUrl(const std::string& response)
{
	Document doc;
	if (response.empty() || !parseData(response, doc) || !doc["data"].IsArray())
		return "";

	const Value& items = doc["data"];
	for (int i = 0; i < (int)items.Size(); i++)
		if (items[i].HasMember("url") && items[i]["url"].IsString())
			return items[i]["url"].GetString();

	return "";
}

static ScraperSearchItem item(const std::string& url)
{
	std::string ext = Utils::String::toLower(Utils::FileSystem::getExtension(url));
	if (ext != ".png" && ext != ".jpg" && ext != ".jpeg")
		ext = ".png";
	return ScraperSearchItem(url, ext);
}

bool SteamGridDBGameRequest::process(const std::string& response, std::vector<ScraperSearchResult>& results)
{
	std::string grid = firstUrl(response);
	std::string hero = firstUrl(getDependencyResponse("heroes"));
	std::string logo = firstUrl(getDependencyResponse("logos"));

	ScraperSearchResult result("SteamGridDB");
	result.mdl.set(MetaDataId::Name, mName);
	result.mdl.set(MetaDataId::Rating, "-1");
	if (!mYear.empty())
		result.mdl.set(MetaDataId::ReleaseDate, Utils::Time::DateTime(Utils::Time::stringToTime(mYear, "%Y")));

	auto settings = Settings::getInstance();
	std::string imageSrc = settings->getString("ScrapperImageSrc");
	std::string thumbSrc = settings->getString("ScrapperThumbSrc");
	std::string logoSrc = settings->getString("ScrapperLogoSrc");

	// <image>: hero by default, box art when "BOX 2D" is chosen as image source
	if (imageSrc == "box-2D" && !grid.empty())
		result.urls[MetaDataId::Image] = item(grid);
	else if (!imageSrc.empty() && !hero.empty())
		result.urls[MetaDataId::Image] = item(hero);
	else if (!imageSrc.empty() && !grid.empty())
		result.urls[MetaDataId::Image] = item(grid);

	// <thumbnail>: box art
	if (!grid.empty() && (thumbSrc == "box-2D" || (thumbSrc.empty() && imageSrc != "box-2D")))
		result.urls[MetaDataId::Thumbnail] = item(grid);

	if (!logo.empty() && !logoSrc.empty())
		result.urls[MetaDataId::Marquee] = item(logo);

	if (!hero.empty() && settings->getBool("ScrapeFanart"))
		result.urls[MetaDataId::FanArt] = item(hero);

	results.push_back(result);
	return true;
}
