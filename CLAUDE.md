# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ZVMS (Zhenhai High School Volunteer Management System) is a FastAPI-based backend service for managing volunteer activities, users, and groups. The system includes both v1 and v2 API endpoints, with v2 being the newer implementation.

## Development Commands

### Running the Application
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Dependencies
```bash
pip install -r requirements.txt
```

## Architecture

### Core Structure
- **main.py**: FastAPI application entry point with router registration, middleware, and scheduled tasks
- **database.py**: MongoDB connection management using Motor (async MongoDB driver)
- **settings.py**: Configuration settings (copy from settings.example.py)
- **config.py**: Application constants and configuration values

### API Organization
- **routers/**: API route handlers organized by resource type
  - Legacy v1 routes: users, activities, groups, exports, imports, logs
  - v2 routes: activities_v2, users_v2, groups_v2, times, activity_statistics
- **typings/**: Pydantic models for request/response validation
- **util/**: Utility functions for calculations, permissions, validation, etc.

### Key Features
- **Dual API versions**: v1 (legacy) and v2 (current) endpoints
- **MongoDB**: Primary database using Motor async driver
- **Scheduled tasks**: Daily computation tasks at midnight and 4 AM HKT
- **SocketIO**: Real-time communication support
- **JWT Authentication**: RSA-based authentication system
- **CORS**: Configured for frontend origins
- **Route redirects**: Automatic singular-to-plural route redirects

### Database Schema
- **zvms**: Main database containing users, activities, groups collections
- **zvms_new**: Secondary database for v2 data migration
- Collections include activities, users, groups, logs, and their v2 equivalents

### Background Tasks
- **compute_time**: Daily volunteer time calculations (midnight HKT)
- **wash_data**: Data cleaning and maintenance (4 AM HKT)

## Configuration

### Required Settings (settings.py)
- `MONGODB_URI`: MongoDB connection string
- `MONGODB_DB`: Database name
- `SECRET_KEY`: JWT signing key

### RSA Keys
- Generate RSA key pair using `generate_key.sh`
- Keys stored in `rsa_private_key.pem` and `rsa_public_key.pem`

## API Endpoints

### Health and Info
- `GET /api/health`: Database connectivity check
- `GET /api/version`: API version information
- `GET /api/cert`: Public RSA certificate

### Main Resources
- `/api/users` and `/api/v2/users`: User management
- `/api/activities` and `/api/v2/activities`: Activity management
- `/api/groups` and `/api/v2/groups`: Group management
- `/api/v2/times`: Time tracking
- `/api/v2/statistics/activities`: Activity statistics
