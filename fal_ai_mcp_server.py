#!/usr/bin/env python3
"""
Fal.ai MCP Server for Image Editing
Compatible with RunBear and other MCP clients
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional
import httpx
import base64
from io import BytesIO
from PIL import Image
import requests
from flask import Flask, request, jsonify

# MCP imports
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    TextContent,
    Tool,
    INVALID_PARAMS,
    INTERNAL_ERROR
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fal-ai-mcp")

class FalAIImageEditor:
    def __init__(self):
        self.api_key = os.environ.get("FAL_KEY")
        if not self.api_key:
            raise ValueError("FAL_KEY environment variable is required")
        
        self.base_url = "https://queue.fal.run"
        
    async def edit_image_flux(self, image_url: str, prompt: str, strength: float = 0.8) -> Dict[str, Any]:
        """Edit image using FLUX image-to-image model"""
        try:
            headers = {
                "Authorization": f"Key {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "image_url": image_url,
                "prompt": prompt,
                "strength": strength,
                "num_inference_steps": 28,
                "guidance_scale": 3.5
            }
            
            async with httpx.AsyncClient() as client:
                # Submit the request
                response = await client.post(
                    f"{self.base_url}/fal-ai/flux/dev/image-to-image",
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "image_url": result["images"][0]["url"],
                        "model": "FLUX Dev",
                        "prompt": prompt
                    }
                else:
                    return {
                        "success": False,
                        "error": f"API request failed: {response.status_code} {response.text}"
                    }
                    
        except Exception as e:
            logger.error(f"Error editing image with FLUX: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def edit_image_qwen(self, image_url: str, prompt: str) -> Dict[str, Any]:
        """Edit image using Qwen Image Edit model (better for text editing)"""
        try:
            headers = {
                "Authorization": f"Key {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "image_url": image_url,
                "prompt": prompt
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/fal-ai/qwen-image-edit",
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "image_url": result["image"]["url"],
                        "model": "Qwen Image Edit",
                        "prompt": prompt
                    }
                else:
                    return {
                        "success": False,
                        "error": f"API request failed: {response.status_code} {response.text}"
                    }
                    
        except Exception as e:
            logger.error(f"Error editing image with Qwen: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def remove_background(self, image_url: str) -> Dict[str, Any]:
        """Remove background from image"""
        try:
            headers = {
                "Authorization": f"Key {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "image_url": image_url
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/fal-ai/imageutils/rembg",
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "image_url": result["image"]["url"],
                        "model": "Background Removal",
                        "prompt": "Remove background"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"API request failed: {response.status_code} {response.text}"
                    }
                    
        except Exception as e:
            logger.error(f"Error removing background: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def upscale_image(self, image_url: str, scale: int = 2) -> Dict[str, Any]:
        """Upscale image"""
        try:
            headers = {
                "Authorization": f"Key {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "image_url": image_url,
                "scale": scale
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/fal-ai/esrgan",
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "image_url": result["image"]["url"],
                        "model": "ESRGAN Upscaler",
                        "prompt": f"Upscale {scale}x"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"API request failed: {response.status_code} {response.text}"
                    }
                    
        except Exception as e:
            logger.error(f"Error upscaling image: {e}")
            return {
                "success": False,
                "error": str(e)
            }

# Initialize the image editor
image_editor = FalAIImageEditor()

# Define available tools
TOOLS = [
    Tool(
        name="edit_image_flux",
        description="Edit an image using FLUX AI model based on a text prompt. Good for general image editing, style changes, object addition/modification.",
        inputSchema={
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "URL of the image to edit (must be publicly accessible)"
                },
                "prompt": {
                    "type": "string", 
                    "description": "Description of how to edit the image (e.g., 'add sunglasses to the person', 'change background to beach')"
                },
                "strength": {
                    "type": "number",
                    "description": "How much to change the image (0.1-1.0, default 0.8). Lower values preserve more of original.",
                    "minimum": 0.1,
                    "maximum": 1.0,
                    "default": 0.8
                }
            },
            "required": ["image_url", "prompt"]
        }
    ),
    Tool(
        name="edit_image_qwen", 
        description="Edit an image using Qwen AI model. Excellent for text editing, precise modifications, and detailed edits.",
        inputSchema={
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "URL of the image to edit (must be publicly accessible)"
                },
                "prompt": {
                    "type": "string",
                    "description": "Description of how to edit the image"
                }
            },
            "required": ["image_url", "prompt"]
        }
    ),
    Tool(
        name="remove_background",
        description="Remove the background from an image, making it transparent.",
        inputSchema={
            "type": "object", 
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "URL of the image to process (must be publicly accessible)"
                }
            },
            "required": ["image_url"]
        }
    ),
    Tool(
        name="upscale_image",
        description="Upscale an image to higher resolution using AI.",
        inputSchema={
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string", 
                    "description": "URL of the image to upscale (must be publicly accessible)"
                },
                "scale": {
                    "type": "integer",
                    "description": "Scale factor (2, 4, or 8). Default is 2.",
                    "enum": [2, 4, 8],
                    "default": 2
                }
            },
            "required": ["image_url"]
        }
    )
]

# Initialize MCP Server
server = Server("fal-ai-image-editor")

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """Return list of available tools"""
    return TOOLS

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool execution"""
    try:
        if name == "edit_image_flux":
            image_url = arguments.get("image_url")
            prompt = arguments.get("prompt")
            strength = arguments.get("strength", 0.8)
            
            if not image_url or not prompt:
                return CallToolResult(
                    content=[TextContent(type="text", text="Error: image_url and prompt are required")],
                    isError=True
                )
            
            result = await image_editor.edit_image_flux(image_url, prompt, strength)
            
        elif name == "edit_image_qwen":
            image_url = arguments.get("image_url")
            prompt = arguments.get("prompt") 
            
            if not image_url or not prompt:
                return CallToolResult(
                    content=[TextContent(type="text", text="Error: image_url and prompt are required")],
                    isError=True
                )
            
            result = await image_editor.edit_image_qwen(image_url, prompt)
            
        elif name == "remove_background":
            image_url = arguments.get("image_url")
            
            if not image_url:
                return CallToolResult(
                    content=[TextContent(type="text", text="Error: image_url is required")],
                    isError=True
                )
            
            result = await image_editor.remove_background(image_url)
            
        elif name == "upscale_image":
            image_url = arguments.get("image_url")
            scale = arguments.get("scale", 2)
            
            if not image_url:
                return CallToolResult(
                    content=[TextContent(type="text", text="Error: image_url is required")],
                    isError=True
                )
            
            result = await image_editor.upscale_image(image_url, scale)
            
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: Unknown tool '{name}'")],
                isError=True
            )
        
        # Format response
        if result["success"]:
            response_text = f"✅ Image edited successfully!\n\n" \
                          f"**Model:** {result['model']}\n" \
                          f"**Prompt:** {result['prompt']}\n" \
                          f"**Result:** {result['image_url']}"
        else:
            response_text = f"❌ Error editing image: {result['error']}"
        
        return CallToolResult(
            content=[TextContent(type="text", text=response_text)],
            isError=not result["success"]
        )
        
    except Exception as e:
        logger.error(f"Error in handle_call_tool: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Internal error: {str(e)}")],
            isError=True
        )

async def main():
    """Run the MCP server"""
    logger.info("Starting Fal.ai Image Editor MCP Server...")
    
    # Check for FAL_KEY
    if not os.environ.get("FAL_KEY"):
        logger.error("FAL_KEY environment variable is required!")
        sys.exit(1)
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="fal-ai-image-editor",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities={}
                )
            )
        )

def create_http_app() -> Flask:
    """Create a Flask app exposing HTTP endpoints for Railway deployment."""
    app = Flask(__name__)
    editor = image_editor

    @app.route("/health", methods=["GET"])
    def health() -> Any:
        return jsonify({"ok": True, "service": "fal-ai-mcp-http"})

    @app.route("/edit/flux", methods=["POST"])
    def edit_flux() -> Any:
        data = request.get_json(force=True, silent=True) or {}
        image_url = data.get("image_url")
        prompt = data.get("prompt")
        strength = float(data.get("strength", 0.8))
        if not image_url or not prompt:
            return jsonify({"success": False, "error": "image_url and prompt are required"}), 400
        result = asyncio.run(editor.edit_image_flux(image_url, prompt, strength))
        return jsonify(result), (200 if result.get("success") else 500)

    @app.route("/edit/qwen", methods=["POST"])
    def edit_qwen() -> Any:
        data = request.get_json(force=True, silent=True) or {}
        image_url = data.get("image_url")
        prompt = data.get("prompt")
        if not image_url or not prompt:
            return jsonify({"success": False, "error": "image_url and prompt are required"}), 400
        result = asyncio.run(editor.edit_image_qwen(image_url, prompt))
        return jsonify(result), (200 if result.get("success") else 500)

    @app.route("/remove-bg", methods=["POST"])
    def remove_bg() -> Any:
        data = request.get_json(force=True, silent=True) or {}
        image_url = data.get("image_url")
        if not image_url:
            return jsonify({"success": False, "error": "image_url is required"}), 400
        result = asyncio.run(editor.remove_background(image_url))
        return jsonify(result), (200 if result.get("success") else 500)

    @app.route("/upscale", methods=["POST"])
    def upscale() -> Any:
        data = request.get_json(force=True, silent=True) or {}
        image_url = data.get("image_url")
        scale = int(data.get("scale", 2))
        if not image_url:
            return jsonify({"success": False, "error": "image_url is required"}), 400
        result = asyncio.run(editor.upscale_image(image_url, scale))
        return jsonify(result), (200 if result.get("success") else 500)

    return app

if __name__ == "__main__":
    # If --http flag is passed or RAILWAY/PORT env exists, run HTTP mode; otherwise run MCP stdio
    run_http = ("--http" in sys.argv) or os.environ.get("PORT") or os.environ.get("RAILWAY_ENVIRONMENT")
    if run_http:
        if not os.environ.get("FAL_KEY"):
            logger.error("FAL_KEY environment variable is required!")
            sys.exit(1)
        port = int(os.environ.get("PORT", "8000"))
        app = create_http_app()
        app.run(host="0.0.0.0", port=port)
    else:
        asyncio.run(main())