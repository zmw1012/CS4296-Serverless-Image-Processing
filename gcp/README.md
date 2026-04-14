# GCP Cloud Run Deployment 

## Architecture 
``` 
Client → POST Request → Cloud Functions (Gen 2) → GCS (Read Image) → Image Processing → Return timing JSON 
``` 

Images are read from Google Cloud Storage (GCS) (not sent in the request body) to support large files (5-10 MB) that exceed typical HTTP payload limits. The response returns timing metrics only, not the processed images. 

## Prerequisites 

1. Create [Google Cloud Account](https://cloud.google.com/)
2. [Google Cloud SDK (gcloud CLI)](https://cloud.google.com/sdk/docs/install) installed and configured
    ```bash
    # Authenticate (first time)
   gcloud auth login
   # Set default project. Replace <your-project-id> with your project name 
   gcloud projects create <your-project-id>
   gcloud config set project <your-project-id>
   # Set default region (match AWS us-east-1: use us-central1)
   gcloud config set run/region us-central1
    ```

3. Enable required APIs (one-time setup):
    ```bash
    gcloud services enable run.googleapis.com storage.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com cloudfunctions.googleapis.com
    ```
4. Create a bucket
    ```bash
    #Set bucket name 
   set BUCKET_NAME=cs4296_image_process-<your-project-id>
    # Link a valid billing account in [Google Cloud](https://console.cloud.google.com/billing)

    #Create a bucket
    gsutil mb -l us-central1 gs://%BUCKET_NAME%
    ```
5. Authorize default service account permissions
    ```bash
    #replace <your-project-id> and <your-service-account>
    gcloud projects add-iam-policy-binding <your-project-id> --member=serviceAccount:<your-service-account> --role=roles/cloudbuild.builds.editor
    gcloud projects add-iam-policy-binding <your-project-id> --member=serviceAccount:<your-service-account> --role=roles/run.admin
    gcloud projects add-iam-policy-binding <your-project-id> --member=serviceAccount:<your-service-account> --role=roles/storage.objectAdmin
    ```

 ## Deploy 
 
 From the `/gcp` directory: 
 
 ### Deploy Cloud Run Service (manual) 
 ```bash 
 # Gcloud run deploy 
 gcloud functions deploy process_image --runtime python311 --trigger-http --entry-point process_image --set-env-vars INPUT_BUCKET=%BUCKET_NAME% --allow-unauthenticated --memory 1Gi --timeout 60s
 ``` 
 
## Upload Dataset
After deploying, upload the dataset images to the created bucket:
    
```bash
gsutil cp -r ../dataset gs://cs4296_image_process-<your-project-id>/
```

## Batch test function performance
```bash
pip install -r requirements.txt
python benchmark.py   --gcp-url <Your Cloud Functions URL>   --runs 5   --concurrency 10   --output gcp_results.csv
```
## Teardown

```bash
#delete cloud functions
gsutil rm -r gs://cs4296_image_process-cs4296-image-process
#delete buckets
gsutil rm -r gs://cs4296_image_process-<Your-project-id>
```