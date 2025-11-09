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
- Documentation
  - [ ] Update with a screenshot of current state
  - [ ] Diagram with the workflow involved
  - [ ] Explanation of LLM prompts and details on bullet journal formats
- Processing
  - [x] conversation agent in config flow
  - [x] Create output storage directory for yaml
  - [x] Storage area for dynamic prompts
  - [x] Multi-modal call that outputs yaml structured output
  - [x] (re)process a media uri on demand
  - [x] Structured output => Journal demo
- State management
  - [x] Metadata store of media source uri sources
  - [x] Compute hashes of media source content to determine changes
  - [ ] Persist journal in .ics
  - [x] Merge existing journal contents with ingested processed media
  - [ ] etag support
- Visibility
  - [x] Entities associated with a device service
  - [x] Sensors exporting diagnostic information like last time processed
  - [x] Sensor exporting # of journal entries
- Journal Entity
  - [ ] Update tests to use service calls for reads
  - [ ] Support for additions to a journal (calendar)
  - [ ] Support for writes to a journal (calendar)
  - [ ] Support for edits to a journal (calendar)
- Assistant API
  - [x] Add journal entities to the prompt
  - [x] Add vector search intent
  - [ ] Calendar search intent
- Vector search
  - [x] create db at starts
  - [x] Query database from tool end to end test
  - [x] persistence of database
  - [x] understand embedding functions
  - [x] support deleting documents and removing from index
  - [ ] support more google models in config flow
  - [ ] support alternative embedding models
  - [ ] delete tenant on integration removal
- [x] support reload of config entries
- [x] support removing config entries, cleaning up database
- [x] make vetordb indexing asynchronous
- [x] reload vector db after updating index
- [x] sensor for # of raw yaml files in total
- [x] sensor for # of pages for each notebook prefix
- [x] sensor with processor counts of total # of processed (total_increasing?)
- [x] monthly/quarterly reflections not showing up, check on details
- [x] Swap local vectordb interface
- [x] Support local vectordb persistence

## Local Development

### Pre-requisites

```bash
$ uv venv
$ source .venv/bin/activate
$ uv pip install -r requirements_dev.txt --prerelease=allow
```

### Prepare Home Assistant

```bash
$ export PYTHONPATH="${PYTHONPATH}:${PWD}"
$ hass -c /workspaces/config --script ensure_config
```

### Run Home Assistant

From then on run home assistant:

```bash
$ hass -c /workspaces/config
```

Running with multiple custom components

```bash
$ cd /workspaces/config
$ ln -s ../../home-assistant-supernote-cloud/custom_components/supernote_cloud custom_components/supernote_cloud
$ ln -s ../../home-assistant-journal-assistant/custom_components/journal_assistant custom_components/journal_assistant
```
