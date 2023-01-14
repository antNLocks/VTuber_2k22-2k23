# VTUBER 2K22 2K23

This repository aims to collect data on French speaking Vtubers.
For now, we are focusing on the Twitch platform but TikTok is next on the wish list.

## Twitch

In order to find potential Vtubers, we scan in real time all Twitch streams in French with a python bot running on a raspberry pi. This bot collects all the streams meeting a specific condition and stores them in a *.csv* file (one *.csv* per day) and pushes these files to a Google Drive. 

From the day the bot was launched until the end of 2022, the condition to keep a stream was to have the Vtuber tag.
But then, the Twitch API changed and now also provides all tags as a list of strings. So we updated our bot: it now checks if a stream has the Vtuber tag id and if the word `Vtuber` is present (case insensitive) in the tag list.

With the new condition, we had many more streams. So much so (5 times more) that we couldn't mix the new streams with the old ones, as they seemed to answer a different question.
We haven't yet looked at what fundamentally differentiates these streams.

Thanks to these streams, we can have access to the broadcasters who have used a Vtuber tag. It can then be interesting to look at the content they publish in order to quantify their level of virtuality (e.g. % of streams with an avatar), their popularity,...

## Repo Architecture

### TwitchBot folder

This folder contains the python scripts designed to run endlessly on a raspberry pi.
There are 2 scripts :
- [twitch_stream_bot](TwitchBot/twitch_stream_bot.py) : it scans all the current streams looking for a Vtuber tag
- [twitch_video_bot](TwitchBot/twitch_video_bot.py) : it retrieves each day all videos published by the broadcasters that have been detected by the `twitch_stream_bot`.


These scripts are mainly composed of a class with a main function (`subroutine`). This `subroutine` is automatically called in a loop by the python library [LoopleSheet](https://github.com/antNLocks/loopleSheet).

The reason for choosing this library is that it uses the Google Sheet API in a transparent way to display information. This makes it possible to follow the good (or not) functioning of the script quickly and anywhere (otherwise, you have to connect with ssh on the server from the same local network). The fact that it can also catch `subroutine` exceptions means that this handling can be offloaded.

It should be noted, however, that obtaining credentials for the Google Sheet API requires some effort.

Another point to note is the use of [drive](https://github.com/odeke-em/drive). This is a command line tool that allows you to connect to a Google Drive with github like commands (`drive push`, `drive pull`,...). Unfortunately, the Out-of-Band workflow was deprecated in October 2022 by Google and `drive` was using it to authenticate. As it is not yet fixed ([this issue](https://github.com/odeke-em/drive/issues/1140)), it is not currently possible to get credentials. As I installed the program before this issue, I didn't have this problem.

*NB* : the scripts use `.json` files to obtain the credentials. These are not pushed to this repository. You need to get your own and put them in the right place (`./twitch_credentials.json` for Twitch and `./TwitchBot/google_credentials.json` for LoopleSheet).

### Data folder

This folder contains all the data collected from the Twitch API.
The structure is as follows :

```
|-Data
    |-aggregated
    |-scattered
        |-tagIds
        |-tagIds_tags
        |-videos
```

Each data folder contains *.csv* files. The `scattered` folder collects the *.csv* files produced by the python bots. Each file corresponds to the data collected **daily** by the bots.
In contrast, the `aggregated` folder contains the same data as `scattered` but processed and aggregated.

In more details:
- `tagIds` contains the streams (grouped by day) which had just the Vtuber tag id
- `tagIds_tags` contains the streams (grouped by day) which have the Vtuber tag id or the word Vtuber in the tag list
- `videos` contains the videos published by the broadcasters that have been detected by the `twitch_stream_bot`
- `aggregated` contains 2 *.csv* :
    - *twitch_streams_vtuber_tagIds.csv* : all the streams which had just the Vtuber tag id
    - *twitch_streams_vtuber_tagIds_tags.csv* : all the streams which have the Vtuber tag id or the word Vtuber in the tag list

### Processing folder

This folder provides jupyter notebooks to process, visualise, understand,... the *.csv* files produced by the python bots.

[processing.ipynb](Processing/processing.ipynb) processes and aggregates the *.csv* files provided by `twitch_stream_bot.py`.

[visualisation.ipynb](Processing/visualisation.ipynb) offers to plot the data collected by `twitch_stream_bot.py` over time.

[enrichment.ipynb](Processing/enrichment.ipynb) tries to mine new data (videos from broadcasters detected by `twitch_stream_bot.py`) for interesting metrics.