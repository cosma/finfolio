# Service Account Setup Guide for FinFolio

This guide walks you through setting up OAuth2 service account credentials for FinFolio to access YouTube Data API v3.

FinFolio uses **service account authentication** (not API keys) to comply with FinFolio Constitution Principle VI (Reliability Over Cleverness). Service accounts provide production-grade, auditable authentication for the official YouTube Data API v3.

## Why Service Accounts?

- **Official YouTube API**: Uses only the official YouTube Data API v3 (no third-party libraries)
- **Production-Ready**: Service account credentials are the standard for server-to-server authentication
- **Secure**: No API keys in plaintext; credentials are restricted to specific scopes
- **Auditable**: All API calls can be traced back to the service account in Google Cloud logs
- **Principle VI Compliant**: "Reliability Over Cleverness" — using the official, supported authentication method

## Prerequisites

- A Google Account (personal or organizational)
- Access to [Google Cloud Console](https://console.cloud.google.com)
- Basic familiarity with Google Cloud

## Step-by-Step Setup

### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click the project dropdown at the top
3. Click **NEW PROJECT**
4. Enter a project name (e.g., `finfolio-youtube`)
5. Click **CREATE**
6. Wait for the project to be created (1-2 minutes)

### 2. Enable YouTube Data API v3

1. In the Google Cloud Console, go to **APIs & Services** → **Library**
2. Search for `YouTube Data API v3`
3. Click **YouTube Data API v3**
4. Click **ENABLE**
5. Wait for the API to be enabled

### 3. Create a Service Account

1. Go to **APIs & Services** → **Credentials**
2. Click **CREATE CREDENTIALS** → **Service Account**
3. Fill in the form:
   - **Service account name**: `finfolio` (or your preferred name)
   - **Service account ID**: Auto-generated (OK to keep default)
   - **Description**: `FinFolio YouTube transcript fetcher`
4. Click **CREATE AND CONTINUE**
5. Click **CONTINUE** on the next screen (no role needed for service accounts accessing public data)
6. Click **DONE**

### 4. Generate a Service Account Key

1. Go to **APIs & Services** → **Credentials**
2. Under **Service Accounts**, click the email address of the `finfolio` service account you just created
3. Go to the **KEYS** tab
4. Click **ADD KEY** → **Create new key**
5. Select **JSON** (for file format)
6. Click **CREATE**
7. A JSON file will download automatically to your computer

**IMPORTANT**: Keep this file safe! Treat it like a password — anyone with this file can access YouTube data via your service account.

### 5. Store the Credentials File

#### Local Development

1. **Rename the file**: Rename the downloaded JSON file to `service-account-key.json` for convenience
2. **Store securely**: Place the file in your project directory or a secure location (e.g., `~/.config/finfolio/`)
3. **Set the environment variable**:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

Add this to your shell profile (`.bashrc`, `.zshrc`, etc.) to make it permanent:

```bash
# ~/.bashrc or ~/.zshrc
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/finfolio/service-account-key.json"
```

4. **Verify**:

```bash
echo $GOOGLE_APPLICATION_CREDENTIALS
```

#### Production Deployment

##### GitHub Actions

1. Go to your GitHub repository
2. Settings → Secrets and Variables → Actions
3. Click **New repository secret**
4. Name: `GOOGLE_APPLICATION_CREDENTIALS`
5. Value: Copy the **entire contents** of the JSON file (not the filename)
6. Click **Add secret**
7. In your GitHub Actions workflow, use:

```yaml
- name: Run finfolio fetch
  env:
    GOOGLE_APPLICATION_CREDENTIALS: ${{ secrets.GOOGLE_APPLICATION_CREDENTIALS }}
  run: make fetch
```

##### Cloud Platforms (GCP, AWS, etc.)

If running on a Google Cloud VM or other cloud platform:

1. **GCP VM**: Use the built-in service account (no file needed)
2. **Other platforms**: Store the JSON file in environment variable or secure secret manager

```bash
# Example: AWS Lambda / CodeBuild
export GOOGLE_APPLICATION_CREDENTIALS=$(aws secretsmanager get-secret-value \
  --secret-id finfolio-service-account --query SecretString --output text)
```

### 6. Test the Setup

Run the fetch command to verify:

```bash
finfolio fetch
```

Expected output:
```json
{"timestamp": "2026-09-24T20:00:00Z", "event": "fetch_start", "status": "success"}
{"timestamp": "2026-09-24T20:00:01Z", "event": "load_credentials", "status": "success", "source": "service_account_file"}
...
```

## Troubleshooting

### Error: `GOOGLE_APPLICATION_CREDENTIALS not set`

**Solution**: Set the environment variable:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
finfolio fetch
```

### Error: `Credentials file not found at /path/to/key.json`

**Solution**: Verify the file path exists:

```bash
ls -la /path/to/service-account-key.json
```

If the file is in the wrong location, move it or update the `GOOGLE_APPLICATION_CREDENTIALS` path.

### Error: `Invalid service account credentials file`

**Solution**: The JSON file is corrupted or malformed. Download a new key:

1. Go to Google Cloud Console → **APIs & Services** → **Credentials**
2. Click the service account email
3. Go to **KEYS** tab
4. Delete the old key (⋮ menu → **Delete**)
5. Click **ADD KEY** → **Create new key** → **JSON**
6. Copy the file to your secure location
7. Update `GOOGLE_APPLICATION_CREDENTIALS` to point to the new file

### Error: `401 Unauthorized`

**Solution**: The service account doesn't have permission to use YouTube API. Verify:

1. YouTube Data API v3 is **enabled** in Google Cloud Console
2. The service account was created **after** enabling the API
3. The credentials file is the correct one from your service account

### Error: `403 Forbidden` or `quotaExceeded`

**Solution**: You've hit YouTube API quota limits. Check:

1. [Google Cloud Console → APIs & Services → YouTube Data API v3 → Quotas](https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas)
2. Daily quota limit is 10,000 units
3. Each operation costs quota units:
   - `search()`: ~100 units
   - `captions().list()`: ~50 units
   - `captions().download()`: ~200 units
4. Wait for quota to reset (typically at midnight Pacific Time)

## Security Best Practices

1. **Never commit the JSON file**: Ensure `.gitignore` includes service account keys:

```
*.json
*-key.json
*service-account*.json
```

2. **Restrict the service account**: In Google Cloud Console, minimize the service account's permissions (read-only to YouTube API)

3. **Rotate keys regularly**: Generate new keys periodically and delete old ones

4. **Monitor usage**: Check [Google Cloud Console → APIs & Services → YouTube Data API v3 → Metrics](https://console.cloud.google.com/apis/api/youtube.googleapis.com/metrics) for suspicious activity

5. **Use separate accounts**: Create different service accounts for development and production

## Next Steps

Once setup is complete:

1. Configure `channels.yaml` with YouTube channels to monitor
2. Run `finfolio fetch` to start fetching transcripts
3. Transcripts will be saved to `storage/transcripts/{video_id}.txt` with timestamps

See the [main README.md](../README.md) for usage instructions.

## Additional Resources

- [Google Cloud Service Accounts Documentation](https://cloud.google.com/docs/authentication/service-accounts)
- [YouTube Data API v3 Documentation](https://developers.google.com/youtube/v3)
- [FinFolio Constitution Principle VI](../CLAUDE.md#principle-vi-reliability-over-cleverness)
