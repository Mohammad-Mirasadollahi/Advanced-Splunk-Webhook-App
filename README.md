# Advanced Splunk Webhook App
This is an enhanced and customizable version of the default Splunk webhook integration. It solves a major limitation in the standard Splunk webhook, which only sent the first row of search results. With this improved app, all search results are sent to the webhook, ensuring complete data delivery.

> **Note:** These scripts were developed with the help of ChatGPT.

# Key Features:
**1- Comprehensive Data Transmission:**
- Unlike the default Splunk webhook, this app sends all rows of the search results, not just the first one.
  
**2- Fail-Safe Webhook Delivery:**
- If the webhook server is down, this app caches the results locally and retries sending them when the server comes back online.

# Key Variables and Their Customization
- **RESULTS_DIR:**\
Default: `/opt/splunk/var/run/splunk/dispatch`
The directory where Splunk stores dispatch data. Update this to match your Splunk installation path if it differs.
- **WEBHOOK_URL:**\
Default: `http://10.1.1.1:8001`
The URL of the webhook where the results will be sent. Replace this with your specific webhook endpoint.

> **Note:** Please update the `webhook_full_result.py` file in the path `...\TA_Custom_Webhook\bin` according to your specific requirements.

## Why Use This App? ##
The default Splunk webhook is limited in its ability to handle large result sets and retry failed transmissions. This advanced solution bridges those gaps, making it more robust and reliable for enterprise use cases.
