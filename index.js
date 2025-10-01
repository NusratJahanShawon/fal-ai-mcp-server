#!/usr/bin/env node

/**
 * MCP HTTP Server for fal.ai Image Modification
 * 
 * This server exposes image modification capabilities through MCP protocol over HTTP
 * Can be hosted on Railway and used with Runbear browser
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import express from "express";
import fetch from "node-fetch";
import cors from "cors";

// Configuration - Set these as environment variables
const FAL_API_KEY = process.env.FAL_API_KEY;
const SLACK_BOT_TOKEN = process.env.SLACK_BOT_TOKEN;
const PORT = process.env.PORT || 3000;

if (!FAL_API_KEY) {
  console.error("Error: FAL_API_KEY environment variable is required");
  process.exit(1);
}

if (!SLACK_BOT_TOKEN) {
  console.error("Error: SLACK_BOT_TOKEN environment variable is required");
  process.exit(1);
}

// Create Express app
const app = express();
app.use(cors());
app.use(express.json());

// Health check endpoint
app.get("/", (req, res) => {
  res.json({
    name: "fal-image-modifier-mcp-server",
    version: "1.0.0",
    status: "running",
    endpoints: {
      mcp: "/sse",
      health: "/health"
    }
  });
});

app.get("/health", (req, res) => {
  res.json({ status: "healthy", timestamp: new Date().toISOString() });
});

// Create MCP server
const server = new Server(
  {
    name: "fal-image-modifier",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Define available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "modify_image",
        description: "Modify an image using AI. Takes an image URL and a text prompt describing the desired modifications. Returns the modified image URL.",
        inputSchema: {
          type: "object",
          properties: {
            image_url: {
              type: "string",
              description: "URL of the image to modify (must be publicly accessible or base64 data URL)",
            },
            prompt: {
              type: "string",
              description: "Text description of how to modify the image (e.g., 'make it anime style', 'add sunset background', 'convert to watercolor painting')",
            },
            model: {
              type: "string",
              description: "AI model to use for modification",
              enum: ["flux-pro-kontext", "flux-dev", "flux-pro"],
              default: "flux-pro-kontext",
            },
            strength: {
              type: "number",
              description: "Modification strength (0.3-1.0). Higher values = more dramatic changes. Default: 0.8",
              minimum: 0.3,
              maximum: 1.0,
              default: 0.8,
            },
          },
          required: ["image_url", "prompt"],
        },
      },
      {
        name: "send_to_slack",
        description: "Send an image to a Slack channel with an optional message",
        inputSchema: {
          type: "object",
          properties: {
            channel_id: {
              type: "string",
              description: "Slack channel ID (e.g., C09FQ934S2Z)",
            },
            image_url: {
              type: "string",
              description: "URL of the image to send",
            },
            message: {
              type: "string",
              description: "Message to include with the image",
              default: "Here's your image!",
            },
          },
          required: ["channel_id", "image_url"],
        },
      },
      {
        name: "modify_and_send_to_slack",
        description: "Complete workflow: Modify an image with AI and automatically send it to a Slack channel",
        inputSchema: {
          type: "object",
          properties: {
            image_url: {
              type: "string",
              description: "URL of the image to modify",
            },
            prompt: {
              type: "string",
              description: "Text description of the modifications to apply",
            },
            channel_id: {
              type: "string",
              description: "Slack channel ID where the modified image will be sent",
            },
            model: {
              type: "string",
              description: "AI model to use",
              enum: ["flux-pro-kontext", "flux-dev", "flux-pro"],
              default: "flux-pro-kontext",
            },
          },
          required: ["image_url", "prompt", "channel_id"],
        },
      },
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    if (name === "modify_image") {
      return await modifyImage(args);
    } else if (name === "send_to_slack") {
      return await sendToSlack(args);
    } else if (name === "modify_and_send_to_slack") {
      return await modifyAndSendToSlack(args);
    } else {
      throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    console.error(`Error executing tool ${name}:`, error);
    return {
      content: [
        {
          type: "text",
          text: `Error: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
});

// Tool implementations

async function modifyImage(args) {
  const { image_url, prompt, model = "flux-pro-kontext", strength = 0.8 } = args;

  console.log(`🎨 Modifying image with prompt: "${prompt}"`);

  // Map model names to fal.ai endpoints
  const modelMap = {
    "flux-pro-kontext": "fal-ai/flux-pro/kontext",
    "flux-dev": "fal-ai/flux/dev/image-to-image",
    "flux-pro": "fal-ai/flux-pro/v1.1",
  };

  const falModel = modelMap[model] || modelMap["flux-pro-kontext"];

  const response = await fetch(`https://fal.run/${falModel}`, {
    method: "POST",
    headers: {
      Authorization: `Key ${FAL_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      prompt: prompt,
      image_url: image_url,
      strength: strength,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(`fal.ai API error: ${error.detail || error.error || "Unknown error"}`);
  }

  const data = await response.json();
  const modifiedImageUrl = data.images[0].url;

  console.log(`✅ Image modified successfully: ${modifiedImageUrl}`);

  return {
    content: [
      {
        type: "text",
        text: `✅ Image modified successfully!\n\n📝 Prompt: ${prompt}\n🎨 Model: ${model}\n💪 Strength: ${strength}\n🔗 Result URL: ${modifiedImageUrl}`,
      },
    ],
  };
}

async function sendToSlack(args) {
  const { channel_id, image_url, message = "Here's your image!" } = args;

  console.log(`📤 Sending image to Slack channel: ${channel_id}`);

  const response = await fetch("https://slack.com/api/chat.postMessage", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${SLACK_BOT_TOKEN}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      channel: channel_id,
      text: `${message}\n\n${image_url}`,
      unfurl_links: true,
      unfurl_media: true,
    }),
  });

  const data = await response.json();

  if (!data.ok) {
    throw new Error(`Slack API error: ${data.error}`);
  }

  console.log(`✅ Image sent to Slack successfully`);

  return {
    content: [
      {
        type: "text",
        text: `✅ Image sent to Slack successfully!\n\n📍 Channel: ${channel_id}\n💬 Message: ${message}\n🔗 Image: ${image_url}`,
      },
    ],
  };
}

async function modifyAndSendToSlack(args) {
  const { image_url, prompt, channel_id, model = "flux-pro-kontext" } = args;

  console.log(`🔄 Starting complete workflow...`);

  // Step 1: Modify the image
  console.log(`🎨 Step 1: Modifying image...`);
  const modifyResult = await modifyImage({ image_url, prompt, model });
  
  // Extract the modified image URL from the result
  const resultText = modifyResult.content[0].text;
  const urlMatch = resultText.match(/Result URL: (https?:\/\/[^\s]+)/);
  const modifiedImageUrl = urlMatch ? urlMatch[1] : null;

  if (!modifiedImageUrl) {
    throw new Error("Failed to extract modified image URL");
  }

  // Step 2: Send to Slack
  console.log(`📤 Step 2: Sending to Slack...`);
  await sendToSlack({
    channel_id,
    image_url: modifiedImageUrl,
    message: `✅ Modified image ready!\n\n📝 Prompt: ${prompt}\n🎨 Model: ${model}`,
  });

  console.log(`✅ Complete workflow finished successfully`);

  return {
    content: [
      {
        type: "text",
        text: `✅ Complete workflow successful!\n\n📝 Prompt: ${prompt}\n🎨 Model: ${model}\n📍 Channel: ${channel_id}\n🔗 Modified Image: ${modifiedImageUrl}\n\n✨ Your modified image has been sent to Slack!`,
      },
    ],
  };
}

// SSE endpoint for MCP
app.get("/sse", async (req, res) => {
  console.log("📡 New SSE connection established");
  
  const transport = new SSEServerTransport("/message", res);
  await server.connect(transport);
  
  res.on("close", () => {
    console.log("📡 SSE connection closed");
  });
});

app.post("/message", async (req, res) => {
  console.log("📨 Received message:", JSON.stringify(req.body, null, 2));
  // The SSE transport handles this automatically
  res.status(200).end();
});

// Start the server
app.listen(PORT, () => {
  console.log("=".repeat(60));
  console.log("🚀 fal.ai Image Modifier MCP Server");
  console.log("=".repeat(60));
  console.log(`📡 Server running on port ${PORT}`);
  console.log(`🌐 Base URL: http://localhost:${PORT}`);
  console.log(`🔌 MCP Endpoint: http://localhost:${PORT}/sse`);
  console.log(`💚 Health Check: http://localhost:${PORT}/health`);
  console.log("=".repeat(60));
  console.log("✅ Ready to accept connections!");
  console.log("");
});