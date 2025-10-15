# GeeDeePerMark

The privacy watermark. Available at https://geedeepermark.cpvo.org/

## Goal

Provide a simple API to have images watermarked with a given text - So Your Apps Will Never Store Unprotected ID Documents Again.

## Definition

### Accepts:

- image and pdf
- text (default: "Confidential")
- text-size: 1, 2, 3, or 4 (default: 3)

### Returns:

- watermarked image

All process runs in memory - no image is ever stored

## Security of your documents

Whey are processed in-memory only and run under a service account (cadd in this case)

## Logs

We run NO LOGS. We're not spies. We may run basic traffic logs at some point to count visitors. No IP, no file copy, no terminal fingerprinting.

## Language

Python. Has lots of libraries, secure and easy to install & read. Shamelessly vibe-coded with VSCode, Cline and free Grok-AI.

Program was designed be as short as possible - ideally, only 1 single file, no compile, in order to be extremely easy to install and run. No Java.

## Available on

https://geedeepermark.cpvo.org

This can't work in CloudFlare Workers - so , self-hosting was necessary.

Plus, it always fun to learn new techs 😃.

Please report if you install it - at least for counting, you don't want to publish the url of your service.

## Origin

Inspired by https://filigrane.beta.gouv.fr/, but this tool has no API

## WARNING

If you change the code, reload your uvicorn or equivalent afterwards.

## Coming next (perhaps)

An UI for your students, users, customers to drop their documents and being able to transmit them securely. I might find the time to write it - or not.

## Author

FredT34, seasonned DPO
