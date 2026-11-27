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

ARG APP_UID=10001
ARG APP_GID=10001

RUN apk --no-cache add ca-certificates tzdata \
    && addgroup -S -g ${APP_GID} appuser \
    && adduser -S -u ${APP_UID} -G appuser appuser \
    && mkdir -p /app/logs \
    && chown -R appuser:appuser /app

WORKDIR /app

# Copy the binary from builder
COPY --from=builder --chown=appuser:appuser /app/invisible-proxy /app/invisible-proxy

USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:8080/ || exit 1

# Run the application
CMD ["./invisible-proxy"]
