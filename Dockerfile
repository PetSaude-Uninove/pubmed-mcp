FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json ./
RUN npm install --omit=dev

# Copy application files
COPY server.mjs ./

# Expose port for streamable HTTP
EXPOSE 8000

# Run the MCP server in streamable HTTP mode
CMD ["node", "server.mjs"]
