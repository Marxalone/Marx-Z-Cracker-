# ZIP Password Cracker Telegram Bot

A Telegram bot that cracks password-protected ZIP files using brute-force methods.

## Features

- Brute-force passwords up to 10 characters long
- Alphanumeric + special character support
- Progress updates during cracking
- File size limit (5MB)
- Automatic cleanup

## Setup

1. Create a Telegram bot via @BotFather and get your token
2. Clone this repository
3. Create `.env` file with your token:


## Usage

1. Start a chat with your bot
2. Send `/start` or `/crack` command
3. Upload your password-protected ZIP file
4. Wait for the password to be cracked

## Deployment Options

### Option 1: Render.com

1. Create a new Web Service
2. Connect your GitHub repository
3. Set environment variables
4. Deploy

### Option 2: VPS

1. SSH into your server
2. Install Docker and Docker Compose
3. Clone this repository
4. Follow the setup steps above
5. Use `docker-compose up -d` to run in background

## Limitations

- Only works with traditional ZIP encryption (not AES)
- Max password length: 10 characters
- Max file size: 5MB
- Performance depends on server CPU