# home-assistant-journal-asssistant

A multi-modal notebook processor for a Bullet Journal.

## Overview

This is a Home Assistant custom component spanwed out the effort to
explore using a [Supernote](https://supernote.com/) e-ink tablet using a [Bullet Journal](https://www.youtube.com/watch?v=fm15cmYU0IM) plus
LLM understanding to develop a personal assistant. This integration will:

- Take as input a media source path and a multi-modal conversation agent
- Process the media source with a set of dynamic prompts
- Expose a parsed RFC5545 JOURNAL as a calendar entity

See https://github.com/allenporter/supernote-llm

## Development plan

- [x] Initial dummy calendar
- Processing
  - [ ] media-source input config flow
  - [ ] conversation agent in config flow
  - [ ] Create output storage directory for yaml
  - [ ] Multi-modal call that outputs yaml structured output
  - [ ] (re)process a media uri on demand
  - [ ] Structured output => Journal demo
- [x] Create monthly journal entity
- [x] Create weekly journal entity
- [x] Create daily journal entity (tasks?)
- [x] Create other journal entries by date created
- Given a directory of notebook yaml contents:
  - [x] Read the notebook file
  - [x] Read through notes grouped by date
  - [x] Check for journal entry on date
  - [x] Create journal entry if it does not already exist
  - [x] Add content to the journal entry
- [x] Test out monthly review
- [x] Test out monthly rapid log
- [x] Test out weekly review
- [x] Test out weekly rapid log

Future work:

- [ ] media source for syncing down from device
- [ ] vector search from a calendar

## Local Development

First time, prepare the environment:

```bash
$ export PYTHONPATH="${PYTHONPATH}:${PWD}"
$ hass -c config --script ensure_config
```

From then on run home assistant:

```bash
$ hass -c config
```
