# Invisible Go Proxy - Dockerfile

# Build stage
FROM golang:1.21-alpine AS builder

WORKDIR /app

# Install dependencies
RUN apk add --no-cache git ca-certificates tzdata

# Copy go mod file
COPY go.mod ./

# Disable go.sum checksum verification completely
ENV GOSUMDB=off
ENV GOPROXY=direct
ENV GONOSUMDB=*

# Download dependencies without checksum verification
RUN go mod download

# Copy source code
COPY . .

# Build the application without any checksum verification
RUN GOSUMDB=off GOPROXY=direct GONOSUMDB=* CGO_ENABLED=0 GOOS=linux go build -mod=mod -a -installsuffix cgo -o invisible-proxy .

# Final stage
FROM alpine:latest

RUN apk --no-cache add ca-certificates tzdata

WORKDIR /root/

# Copy the binary from builder
COPY --from=builder /app/invisible-proxy .

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:8080/ || exit 1

# Run the application
CMD ["./invisible-proxy"]
