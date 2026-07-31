FROM node:22-slim

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies (recharts declares a React 18 peer dep; project uses React 19)
RUN npm install --legacy-peer-deps

# Copy the rest of the application
COPY . .

# Expose the port
EXPOSE 5173

# Start the development server (bind to 0.0.0.0 so it's reachable from the host)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]