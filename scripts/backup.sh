#!/bin/bash

# ERP System Database Backup Script
# This script creates automated backups of the PostgreSQL database

set -e  # Exit on any error

# Configuration
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-erp_system}"
DB_USER="${DB_USER:-erp_user}"
BACKUP_DIR="/backups"
DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="erp_backup_${DATE}.sql"
RETENTION_DAYS=30

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

log "🚀 Starting database backup..."

# Check if PostgreSQL is accessible
if ! pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -q; then
    error "❌ Cannot connect to PostgreSQL database"
    exit 1
fi

log "✅ Database connection successful"

# Create backup
log "📦 Creating backup: ${BACKUP_FILE}"

if pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
    --no-password --clean --if-exists --create \
    --format=custom --compress=9 \
    --file="${BACKUP_DIR}/${BACKUP_FILE}.dump" 2>/dev/null; then
    
    # Also create a plain SQL backup for easier restoration
    pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
        --no-password --clean --if-exists --create \
        --file="${BACKUP_DIR}/${BACKUP_FILE}" 2>/dev/null
    
    log "✅ Backup created successfully"
    
    # Get backup size
    BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}.dump" | cut -f1)
    log "📊 Backup size: ${BACKUP_SIZE}"
    
else
    error "❌ Backup failed"
    exit 1
fi

# Compress the SQL backup
log "🗜️ Compressing SQL backup..."
gzip "${BACKUP_DIR}/${BACKUP_FILE}"

# Clean up old backups
log "🧹 Cleaning up old backups (keeping last ${RETENTION_DAYS} days)..."

# Find and delete backups older than retention period
find "${BACKUP_DIR}" -name "erp_backup_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true
find "${BACKUP_DIR}" -name "erp_backup_*.dump" -type f -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true

# Count remaining backups
BACKUP_COUNT=$(find "${BACKUP_DIR}" -name "erp_backup_*.dump" -type f | wc -l)
log "📁 Total backups remaining: ${BACKUP_COUNT}"

# Create backup report
cat > "${BACKUP_DIR}/backup_report_${DATE}.txt" << EOF
ERP System Backup Report
========================
Date: $(date)
Database: ${DB_NAME}
Host: ${DB_HOST}:${DB_PORT}
User: ${DB_USER}
Backup File: ${BACKUP_FILE}.dump
Compressed SQL: ${BACKUP_FILE}.gz
Size: ${BACKUP_SIZE}
Status: SUCCESS
Total Backups: ${BACKUP_COUNT}
Retention: ${RETENTION_DAYS} days

Files Created:
- ${BACKUP_DIR}/${BACKUP_FILE}.dump (Custom format)
- ${BACKUP_DIR}/${BACKUP_FILE}.gz (Compressed SQL)
EOF

log "📋 Backup report created: backup_report_${DATE}.txt"

# Verify backup integrity
log "🔍 Verifying backup integrity..."
if pg_restore --list "${BACKUP_DIR}/${BACKUP_FILE}.dump" > /dev/null 2>&1; then
    log "✅ Backup integrity verified"
else
    warning "⚠️ Backup integrity check failed - backup may be corrupted"
fi

log "🎉 Backup process completed successfully!"

# Optional: Send notification (if configured)
if [ ! -z "${BACKUP_WEBHOOK_URL}" ]; then
    curl -X POST "${BACKUP_WEBHOOK_URL}" \
        -H "Content-Type: application/json" \
        -d "{\"message\": \"ERP System backup completed successfully\", \"date\": \"$(date)\", \"size\": \"${BACKUP_SIZE}\"}" \
        2>/dev/null || warning "Failed to send backup notification"
fi

exit 0 