# Google Cloud Wildcard HTTPS Setup for *.yourdomain.com (Cloud Run + Certificate Manager + Load Balancer)

This guide shows how to set up a fully working wildcard HTTPS endpoint (e.g. `*.yourdomain.com`) using:

- Google Cloud Run
- Google-managed wildcard certificate (via Certificate Manager)
- HTTPS Load Balancer
- Cloudflare DNS (or another DNS provider)

---

## ✅ Prerequisites

- Google Cloud project (e.g. `my-project-id`)
- `gcloud` CLI installed and authenticated
- A public domain you control (e.g. `yourdomain.com`)
- Access to DNS (e.g. Cloudflare) to update records

---

## 🔧 Step 1: Enable Required Services

```bash
gcloud services enable compute.googleapis.com   certificatemanager.googleapis.com   run.googleapis.com   --project=YOUR_PROJECT_ID
```

---

## 📦 Step 2: Deploy Your Cloud Run Service

```bash
gcloud run deploy YOUR_SERVICE_NAME   --source=.   --region=us-west1   --platform=managed   --allow-unauthenticated   --project=YOUR_PROJECT_ID
```

---

## 🌐 Step 3: Reserve a Global Static IP

```bash
gcloud compute addresses create YOUR_STATIC_IP_NAME   --global   --project=YOUR_PROJECT_ID
```

Get the IP:

```bash
gcloud compute addresses describe YOUR_STATIC_IP_NAME   --global   --project=YOUR_PROJECT_ID   --format="value(address)"
```

---

## 🛡️ Step 4: Create DNS Authorization for Certificate

```bash
gcloud certificate-manager dns-authorizations create yourdomain-auth   --domain="yourdomain.com"   --project=YOUR_PROJECT_ID
```

Add the output CNAME record to your DNS (Cloudflare, etc.):

| Type  | Name               | Target (.goog) domain                    | Proxy |
|-------|--------------------|------------------------------------------|--------|
| CNAME | _acme-challenge    | e.g. `xyz.auth.certificatemanager.goog` | DNS Only

---

## 🔐 Step 5: Create the Wildcard Certificate

```bash
gcloud certificate-manager certificates create yourdomain-wildcard-cert   --domains="yourdomain.com,*.yourdomain.com"   --dns-authorizations="yourdomain-auth"   --location=global   --project=YOUR_PROJECT_ID
```

Wait until:

```bash
gcloud certificate-manager certificates describe yourdomain-wildcard-cert   --location=global   --project=YOUR_PROJECT_ID
```

...shows `state: ACTIVE`.

---

## 🌐 Step 6: Create Serverless NEG and Backend Service

```bash
gcloud compute network-endpoint-groups create my-neg   --region=us-west1   --network-endpoint-type=serverless   --cloud-run-service=YOUR_SERVICE_NAME   --project=YOUR_PROJECT_ID

gcloud compute backend-services create my-backend   --global   --protocol=HTTP   --load-balancing-scheme=EXTERNAL_MANAGED   --project=YOUR_PROJECT_ID

gcloud compute backend-services add-backend my-backend   --global   --network-endpoint-group=my-neg   --network-endpoint-group-region=us-west1   --project=YOUR_PROJECT_ID
```

---

## 🚏 Step 7: Create URL Map and Certificate Map

```bash
gcloud compute url-maps create my-url-map   --default-service=my-backend   --project=YOUR_PROJECT_ID

gcloud certificate-manager maps create my-cert-map   --location=global   --project=YOUR_PROJECT_ID

gcloud certificate-manager maps entries create wildcard-entry   --map=my-cert-map   --location=global   --hostname="*.yourdomain.com"   --certificates=yourdomain-wildcard-cert   --project=YOUR_PROJECT_ID
```

---

## 🚦 Step 8: Create Target HTTPS Proxy and Forwarding Rule

```bash
gcloud compute target-https-proxies create my-https-proxy   --url-map=my-url-map   --certificate-map=projects/YOUR_PROJECT_ID/locations/global/certificateMaps/my-cert-map   --project=YOUR_PROJECT_ID
```

```bash
gcloud compute forwarding-rules create my-forwarding-rule   --load-balancing-scheme=EXTERNAL_MANAGED   --network-tier=PREMIUM   --address=YOUR_STATIC_IP_NAME   --global   --target-https-proxy=my-https-proxy   --ports=443   --project=YOUR_PROJECT_ID
```

---

## 🌍 Step 9: Point DNS to the Load Balancer

In Cloudflare (or DNS provider):

| Type | Name | Value (Static IP)      | Proxy |
|------|------|------------------------|--------|
| A    | *    | YOUR RESERVED IP       | DNS Only

---

## ✅ Step 10: Test It

```bash
curl -v https://foo.yourdomain.com
```

Expected response:

```
Hello from foo
```

---

## 🧼 Optional: Clean Up

```bash
gcloud compute forwarding-rules delete my-forwarding-rule --global
gcloud compute target-https-proxies delete my-https-proxy
gcloud compute url-maps delete my-url-map
gcloud compute backend-services delete my-backend --global
gcloud compute addresses delete YOUR_STATIC_IP_NAME --global
gcloud compute network-endpoint-groups delete my-neg --region=us-west1
gcloud certificate-manager certificates delete yourdomain-wildcard-cert --location=global
gcloud certificate-manager dns-authorizations delete yourdomain-auth --location=global
gcloud certificate-manager maps entries delete wildcard-entry --map=my-cert-map --location=global
gcloud certificate-manager maps delete my-cert-map --location=global
```
