# Invisible Go Proxy - Dockerfile

# Build stage
FROM golang:1.27-alpine AS builder

WORKDIR /app

# Install dependencies
RUN apk add --no-cache git ca-certificates tzdata

COPY go.mod go.sum ./

RUN go mod download

# Copy source code
COPY . .

RUN CGO_ENABLED=0 GOOS=linux go build -mod=readonly -a -installsuffix cgo -o invisible-proxy .

# Final stage
FROM alpine:3.24

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
