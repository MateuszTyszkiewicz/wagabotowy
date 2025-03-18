# Wagabotowy

## Description

Hi!

Wagabotowy is our Python- and LLM-based Discord Bot. LLMs may be run either via Google Gemini API (preffered way I would say) or locally.

## Features

Wagabotowy:
- Summarizes YouTube videos linked in messages,
- Summarizes channels's discussions up to 300 messages back,
- Describes words passed to the bot using the name of the channel as a context (experimental).

## Setting up the app

1. Create a new Application in a Discord Developer Portal - https://discord.com/developers/applications
2. Configure the bot in the "Bot" section. Generate and save the bot token.
3. In "OAuth2" section follow Discord instructions and generate the URL with correct permissions set ("Bot" in SCOPES -> "Send messages", "Read message history" and "View channels" in BOT PERMISSIONS).
4. Add the bot to the Discord server.
7. Generate API key for Google Gemini API to run Gemini models -  
https://aistudio.google.com/app/apikey?hl=pl.  
For most use cases free tier should be enough.

### Running in a Podman container

For now Podman is a recommended container engine as it allows to create and pass secrets to the container in an easy way. Follow these steps to run the app in the container:

1. Clone the repository.

2. Create the app image:
```podman build -t wagabotowy:latest .```

3. Pass secrets to Podman:  
```echo -n <your_discord_bot_token> | podman secret create DISCORD_BOT_TOKEN -```  
```echo -n <your_gemini_api_key> | podman secret create GOOGLE_AI_API_KEY -```

4. Run the container:  
```podman run --secret GOOGLE_AI_API_KEY --secret DISCORD_BOT_TOKEN --user 1000:1000 --detach wagabotowy```


### Running locally

Follow these steps to set up the app locally:

1. Clone the repository.

2. If you use Mamba/Conda:

Create an environment using command:  
```mamba create -n <name> python=3.12```

It should work in a similar way when if you use venvs.

3. Navigate into the project directory.

4. Install dependencies using command:

```pip install -r requirements.txt```

#### Running the bot

To run the bot locally navigate to the project directory, activate the environment and use command:

```python discord\discord_summarizer.py```

### Available flags

`--local` - LLM calculations are made locally, not recommended if Gemini API is available.   
`--ez_mode` - run lighter models, requires much less computing power. Works only with --local flag.

## License

MIT License
