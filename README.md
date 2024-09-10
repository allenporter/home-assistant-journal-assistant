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
- [ ] media-source input config flow
- [ ] conversation agent in config flow
- [ ] Create output storage directory for yaml
- [ ] Multi-modal call that outputs yaml structured output
- [ ] (re)process a media uri on demand
- [ ] Structured output => Journal demo
- [ ] For notebook entries
- [ ] Create monthly journal entity
- [ ] Create weekly journal entity
- [ ] Create daily journal entity (tasks?)
- [ ] Create other journal entries by date created
- Given a directory of notebook yaml contents:
  - [ ] Read the notebook file
  - [ ] Read through notes grouped by date
  - [ ] Check for journal entry on date
  - [ ] Create journal entry if it does not already exist
  - [ ] Add content to the journal entry

Future work:
- [ ] media source for syncing down from device
- [ ] vector search from a calendar
