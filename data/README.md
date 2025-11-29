# Data Folder

This folder contains the Facebook Ads dataset used by the multi-agent analysis system.

## Files

- `dataset.csv` - Sample dataset with 5 entries for testing
- `dataset_full.csv` - Full dataset with all entries for production use

## Required CSV Format

The CSV file must contain the following columns in order:

| Column           | Type    | Description                                             |
| ---------------- | ------- | ------------------------------------------------------- |
| campaign_name    | string  | Name of the advertising campaign                        |
| adset_name       | string  | Name of the ad set within the campaign                  |
| date             | string  | Date of the record in YYYY-MM-DD format                 |
| spend            | float   | Amount spent in USD                                     |
| impressions      | integer | Number of times the ad was displayed                    |
| clicks           | float   | Number of clicks on the ad                              |
| ctr              | float   | Click-through rate (clicks / impressions)               |
| purchases        | integer | Number of purchases attributed to the ad                |
| revenue          | float   | Revenue generated in USD                                |
| roas             | float   | Return on ad spend (revenue / spend)                    |
| creative_type    | string  | Type of creative used (Image, Video, UGC, Carousel)     |
| creative_message | string  | The ad copy or message text                             |
| audience_type    | string  | Target audience segment (Broad, Lookalike, Retargeting) |
| platform         | string  | Platform where ad was shown (Facebook, Instagram)       |
| country          | string  | Country code (US, UK, IN, etc.)                         |

## Column Details

### Numeric Columns

- `spend` - Can be empty (will be treated as 0)
- `impressions` - Must be a positive integer
- `clicks` - Can be a float due to attribution models
- `ctr` - Decimal value between 0 and 1 (e.g., 0.0183 = 1.83%)
- `purchases` - Must be a non-negative integer
- `revenue` - Can be empty (will be treated as 0)
- `roas` - Calculated as revenue / spend

### Categorical Columns

- `creative_type` - One of: Image, Video, UGC, Carousel
- `audience_type` - One of: Broad, Lookalike, Retargeting
- `platform` - One of: Facebook, Instagram
- `country` - ISO 3166-1 alpha-2 country code

## Example Row

```csv
Men ComfortMax Launch,Adset-1 Retarget,2025-01-01,640.09,235597,4313.0,0.0183,80,1514.28,2.37,Image,Breathable organic cotton that moves with you — limited offer on men briefs.,Broad,Facebook,US
```

## Notes

- The first row must be the header row with exact column names
- Date format must be YYYY-MM-DD
- Empty numeric values are acceptable and will be handled by the data loader
- Campaign names may contain variations (spaces, underscores, hyphens) which are normalized during processing
