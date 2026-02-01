# Control Plane Deployment

The Estelle Manor Padel Booking System is deployed to Control Plane in the `george-crosby-015c08` organization.

## Deployment Information

- **Organization**: george-crosby-015c08
- **GVC**: dev
- **Workload Name**: gc-estelle
- **Endpoint**: https://gc-estelle-kard0ecp8znrp.bz78we1mvwy3m.cpln.app
- **Internal Name**: gc-estelle.dev.cpln.local
- **Location**: aws-eu-central-1 (Frankfurt)

## Resources

The deployment consists of:

1. **Identity**: `gc-estelle-identity` - Workload identity for the booking service
2. **Workload**: `gc-estelle` - Standard workload running the booking container

## Container Configuration

- **Image**: `/org/george-crosby-015c08/image/gc-estelle-padel-booking:latest`
- **CPU**: 500m
- **Memory**: 1Gi
- **Type**: Standard (always running, not serverless)
- **Replicas**: 1 (min: 1, max: 1)

## Environment Variables

All sensitive credentials are passed via Terraform variables:
- `ESTELLE_USERNAME` - Estelle Manor login
- `ESTELLE_PASSWORD` - Estelle Manor password
- `DISCORD_WEBHOOK_URL` - Discord webhook for notifications

Configuration settings:
- `DRY_RUN`: false (live booking mode)
- `LOG_LEVEL`: INFO
- `PRE_LOGIN_MINUTES`: 10
- `EVENTS_MONITORING_ENABLED`: true
- `EVENTS_CHECK_INTERVAL_HOURS`: 6

## API Endpoints

Base URL: https://gc-estelle-kard0ecp8znrp.bz78we1mvwy3m.cpln.app

- `GET /health` - Health check endpoint
- `GET /bookings` - List all bookings
- `POST /bookings/upload` - Upload CSV with bookings
- `DELETE /bookings/{id}` - Delete a booking
- `GET /events/recent` - List recent events
- `POST /events/check-now` - Trigger event check
- `POST /test/notification` - Test Discord notification

## Deployment Process

### Building and Pushing Docker Image

```bash
# Build the Docker image
docker build -t gc-estelle-padel-booking:latest .

# Login to Control Plane registry
cpln image docker-login --org george-crosby-015c08

# Tag and push
docker tag gc-estelle-padel-booking:latest george-crosby-015c08.registry.cpln.io/gc-estelle-padel-booking:latest
docker push george-crosby-015c08.registry.cpln.io/gc-estelle-padel-booking:latest
```

Or use the provided script:
```bash
./build_push.sh
```

### Deploying with Terraform

```bash
cd terraform

# Initialize Terraform (first time only)
terraform init

# Set credentials
export TF_VAR_estelle_username='your.email@example.com'
export TF_VAR_estelle_password='your_password'
export TF_VAR_discord_webhook_url='https://discord.com/api/webhooks/...'

# Plan changes
terraform plan

# Apply changes
terraform apply
```

## Updating the Service

### Update Code

1. Make code changes locally
2. Build and push new Docker image:
   ```bash
   ./build_push.sh --tag v1.1.0
   ```
3. Update `terraform/terraform.tfvars` with new image tag
4. Apply Terraform changes:
   ```bash
   cd terraform && terraform apply
   ```

### Update Configuration

1. Edit `terraform/terraform.tfvars` to change configuration
2. Apply changes:
   ```bash
   cd terraform && terraform apply
   ```

## Monitoring

### View Logs

```bash
# Using Control Plane CLI
cpln workload logs gc-estelle --org george-crosby-015c08 --gvc dev --follow

# View specific container logs
cpln workload logs gc-estelle --org george-crosby-015c08 --gvc dev --container booking --follow
```

### Check Status

```bash
# Workload status
cpln workload get gc-estelle --org george-crosby-015c08 --gvc dev

# Replica status
cpln workload replica get gc-estelle --org george-crosby-015c08 --gvc dev
```

### Health Check

```bash
curl https://gc-estelle-kard0ecp8znrp.bz78we1mvwy3m.cpln.app/health
```

## Scaling

The service is configured with autoscaling disabled and fixed at 1 replica:
- `min_replicas`: 1
- `max_replicas`: 1
- `metric`: disabled

This ensures the booking scheduler always runs and doesn't miss midnight booking windows.

## Data Persistence

**IMPORTANT**: Currently, the workload uses the container filesystem for data storage. This means:
- Database and browser state are stored inside the container
- Data will be lost if the container is recreated
- Not suitable for long-term production use

**Recommended for Production**: Mount external storage (S3, GCS, Azure Blob) for persistence:

```hcl
# In terraform/workloads.tf
volume {
  uri  = "s3://your-bucket/gc-estelle"
  path = "/app/data"
}
```

## Troubleshooting

### Service Not Responding

1. Check workload status:
   ```bash
   cpln workload get gc-estelle --org george-crosby-015c08 --gvc dev
   ```

2. View recent logs:
   ```bash
   cpln workload logs gc-estelle --org george-crosby-015c08 --gvc dev --tail 100
   ```

3. Check replica health:
   ```bash
   cpln workload replica get gc-estelle --org george-crosby-015c08 --gvc dev
   ```

### Image Not Found

Ensure the image was pushed successfully:
```bash
cpln image get gc-estelle-padel-booking --org george-crosby-015c08
```

### Permission Issues

Verify the workload identity has correct permissions:
```bash
cpln identity get gc-estelle-identity --org george-crosby-015c08 --gvc dev
```

## Cleanup

To remove the deployment:

```bash
cd terraform
terraform destroy
```

This will remove:
- The workload
- The identity
- All associated resources

Note: The Docker image in the registry will remain and must be deleted separately if needed.

## GitHub Repository

Code is available at: https://github.com/dockerised/estelle

## Support

For Control Plane specific issues, consult:
- [Control Plane Documentation](https://docs.controlplane.com)
- [Control Plane CLI Reference](https://docs.controlplane.com/reference/cli)
- [Terraform Provider Documentation](https://registry.terraform.io/providers/controlplane-com/cpln/latest/docs)
