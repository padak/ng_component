#!/bin/bash
# Quick start script for the Salesforce Mock API

echo "Starting Salesforce REST API Mock Server..."
echo "=========================================="
echo ""
echo "Server will be available at: http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

uvicorn main:app --reload --host 0.0.0.0 --port 8000
