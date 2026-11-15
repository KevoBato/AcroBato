#pragma once

#ifndef ES_APP_SCRAPERS_STEAMGRIDDB_SCRAPER_H
#define ES_APP_SCRAPERS_STEAMGRIDDB_SCRAPER_H

// AcroBato: SteamGridDB (https://www.steamgriddb.com) artwork scraper.
// Uses the user's own API key (Settings "SteamGridDBApiKey", from steamgriddb.com >
// Preferences > API). Provides box art (grids), hero images (fan art / main image) and
// logos (marquee); SteamGridDB has no descriptions or other metadata besides the name.

#include "scrapers/Scraper.h"

class SteamGridDBScraper : public Scraper
{
public:
	void generateRequests(const ScraperSearchParams& params,
		std::queue<std::unique_ptr<ScraperRequest>>& requests,
		std::vector<ScraperSearchResult>& results) override;

	bool isSupportedPlatform(SystemData* system) override { return true; }

	const std::set<ScraperMediaSource>& getSupportedMedias() override;

	static bool hasApiKey();
};

// search/autocomplete -> one SteamGridDBGameRequest per matching game
class SteamGridDBSearchRequest : public ScraperHttpRequest
{
public:
	SteamGridDBSearchRequest(std::queue<std::unique_ptr<ScraperRequest>>& requestsWrite, std::vector<ScraperSearchResult>& resultsWrite,
		const std::string& url, HttpReqOptions* options, bool isManualScrape)
		: ScraperHttpRequest(resultsWrite, url, options), mRequestQueue(&requestsWrite), mIsManualScrape(isManualScrape)
	{
		if (options != nullptr)
			mOptions = *options;
	}

	virtual bool retryOn249() { return !mIsManualScrape; }

protected:
	bool process(const std::string& response, std::vector<ScraperSearchResult>& results) override;

	std::queue<std::unique_ptr<ScraperRequest>>* mRequestQueue;
	HttpReqOptions mOptions;
	bool mIsManualScrape;
};

// grids for one game, with heroes and logos fetched as dependencies
class SteamGridDBGameRequest : public ScraperHttpRequest
{
public:
	SteamGridDBGameRequest(std::vector<ScraperSearchResult>& resultsWrite, int gameId, const std::string& name,
		const std::string& year, HttpReqOptions* options, bool isManualScrape);

	virtual bool retryOn249() { return !mIsManualScrape; }

protected:
	bool process(const std::string& response, std::vector<ScraperSearchResult>& results) override;

	std::string mName;
	std::string mYear;
	bool mIsManualScrape;
};

#endif // ES_APP_SCRAPERS_STEAMGRIDDB_SCRAPER_H
