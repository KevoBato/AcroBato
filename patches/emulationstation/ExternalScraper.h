#pragma once

#ifndef ES_APP_SCRAPERS_EXTERNAL_SCRAPER_H
#define ES_APP_SCRAPERS_EXTERNAL_SCRAPER_H

// AcroBato: scrapers implemented by the `acrobato-scrape` helper (packaging/scraper/acrobato_scrape.py):
// LaunchBox Games Database, libretro thumbnails and GameTDB. None needs an account.
// The helper runs on a background thread and prints a JSON list of results.

#include "scrapers/Scraper.h"

#include <atomic>
#include <thread>

class ExternalScraper : public Scraper
{
public:
	ExternalScraper(const std::string& source, std::set<ScraperMediaSource> medias) : mSource(source), mMedias(medias) { }

	void generateRequests(const ScraperSearchParams& params,
		std::queue<std::unique_ptr<ScraperRequest>>& requests,
		std::vector<ScraperSearchResult>& results) override;

	bool isSupportedPlatform(SystemData* system) override { return true; }

	const std::set<ScraperMediaSource>& getSupportedMedias() override { return mMedias; }

private:
	std::string mSource;
	std::set<ScraperMediaSource> mMedias;
};

class ExternalScraperRequest : public ScraperRequest
{
public:
	ExternalScraperRequest(std::vector<ScraperSearchResult>& resultsWrite, const std::string& scraperName, const std::string& command);
	~ExternalScraperRequest();

	void update() override;

private:
	std::string mScraperName;
	std::thread mThread;
	std::atomic<bool> mDone;
	std::string mOutput;
};

// Fills result.urls from {"box2d", "screenshot", ...} following the scraper settings
// (image / box / logo source, fan art, box back).
void applyScrapedMedia(ScraperSearchResult& result, const std::map<std::string, std::string>& media);

#endif // ES_APP_SCRAPERS_EXTERNAL_SCRAPER_H
