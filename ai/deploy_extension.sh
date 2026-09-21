#!/bin/bash

# Retail Action Recorder Extension Deployment Script

echo "🚀 Starting Retail Action Recorder Extension Deployment..."

# Create deployment directory
DEPLOY_DIR="extension_deployment"
mkdir -p $DEPLOY_DIR

# Copy extension files
echo "📁 Copying extension files..."
cp static/manifest.json $DEPLOY_DIR/
cp static/background.js $DEPLOY_DIR/
cp static/content.js $DEPLOY_DIR/
cp static/popup.js $DEPLOY_DIR/
cp static/popup.html $DEPLOY_DIR/

# Create Chrome extension package
echo "📦 Creating Chrome extension package..."
cd $DEPLOY_DIR
zip -r ../retail-action-recorder-chrome.zip ./*
cd ..

# Create Firefox extension package (same files for now)
echo "🦊 Creating Firefox extension package..."
cd $DEPLOY_DIR
zip -r ../retail-action-recorder-firefox.zip ./*
cd ..

# Copy to static directory for web serving
echo "🌐 Copying to static directory..."
cp retail-action-recorder-chrome.zip static/
cp retail-action-recorder-firefox.zip static/

echo "✅ Deployment completed!"
echo ""
echo "📋 Files created:"
echo "  - retail-action-recorder-chrome.zip"
echo "  - retail-action-recorder-firefox.zip"
echo "  - static/retail-action-recorder-chrome.zip"
echo "  - static/retail-action-recorder-firefox.zip"
echo ""
echo "🔧 Installation Instructions:"
echo "  Chrome:"
echo "    1. Go to chrome://extensions/"
echo "    2. Enable 'Developer mode'"
echo "    3. Click 'Load unpacked'"
echo "    4. Select the extension_deployment folder"
echo ""
echo "  Firefox:"
echo "    1. Go to about:addons"
echo "    2. Click the gear icon"
echo "    3. Select 'Install Add-on From File...'"
echo "    4. Choose the manifest.json file from extension_deployment folder"
echo ""
echo "🎯 Extension Features:"
echo "  - Records user actions (clicks, form changes)"
echo "  - Sends data to: https://your-domain.com/api/v1/interactions/extension-action"
echo "  - Includes client_recommendation field for additional notes"
echo "  - Supports both Chrome and Firefox" 