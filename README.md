# Tridorian customized services - Coding Example

This repository serves as a comprehensive example created by the Presales Solution Architecture team to demonstrate best practices in building microservices for each custom-solution projects. It showcases real-world implementations of common  features using modern technologies and cloud services.

## Purpose

This repository is designed to:
- Demonstrate practical implementations of common features
- Showcase integration patterns with Google Cloud Platform services
- Provide reference architecture for microservices development
- Serve as a learning resource for engineering teams
- Illustrate best practices in API design, security, and deployment

## Target Audience

This example is particularly valuable for:
- Engineering teams looking to implement similar features
- Developers learning about microservices architecture
- Solution architects designing platforms
- Teams planning to use Google Cloud Platform services
- Anyone interested in FastAPI and modern Python development

## Projects

### 1. [ShopGlobal Text Search](https://github.com/tridorian/presales-example/tree/main/shopglobal_text_search)
A FastAPI-based search service that integrates with Google Vertex AI Search to provide product search functionality. Features include:
- Natural language product search
- Support for both Thai and English queries
- WordPress WooCommerce Flatsome theme integration
- API key authentication
- Docker and Cloud Run deployment support

### 2. [ShopGlobal Image Search](https://github.com/tridorian/presales-example/tree/main/shopglobal_image_search)
A FastAPI service that uses Google's Gemini Pro Vision model to analyze images and generate descriptive captions. Features include:
- Image analysis and caption generation
- Multi-language support (Thai/English)
- Automatic image size optimization
- API key authentication
- Docker and Cloud Run deployment support

### 3. [ShopGlobal Line Chat](https://github.com/tridorian/presales-example/tree/main/shopglobal_line_chat)
IMPORTANT: ⚠️ WORK IN PROGRESS!!! ⚠️
A FastAPI application that logs conversations from Dialogflow CX webhooks to BigQuery. Features include:
- Conversation logging to BigQuery
- Dialogflow CX webhook integration
- API key authentication
- Comprehensive error handling and logging

## Postman Collection 🚀
### ShopChannel
Development: ⬇️ [PostmanCollection_ShopGlobal_Dev.json](https://github.com/tridorian/presales-example/blob/main/PostmanCollection_ShopGlobal_Dev.json)

## API KEY
The API key can be obtained by creating a new service acount for the Google Cloud's project, then assign necessary permission to it.

