# Billing API Documentation

Complete API documentation for billing, subscription, and usage management endpoints.

**Related Documentation:**

- [User API](./user.md) - For authentication endpoints
- [Contacts API](./contacts.md) - For contact management endpoints
- [Companies API](./company.md) - For company management endpoints

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [CORS Testing](#cors-testing)
- [Billing Endpoints](#billing-endpoints)
  - [GET /api/v1/billing/](#get-apiv1billing---get-billing-information)
  - [GET /api/v1/billing/plans/](#get-apiv1billingplans---get-subscription-plans)
  - [GET /api/v1/billing/addons/](#get-apiv1billingaddons---get-addon-packages)
  - [POST /api/v1/billing/subscribe/](#post-apiv1billingsubscribe---subscribe-to-plan)
  - [POST /api/v1/billing/addon/](#post-apiv1billingaddon---purchase-addon-credits)
  - [POST /api/v1/billing/cancel/](#post-apiv1billingcancel---cancel-subscription)
  - [GET /api/v1/billing/invoices/](#get-apiv1billinginvoices---get-invoice-history)
- [Subscription Plans](#subscription-plans)
- [Addon Packages](#addon-packages)
- [Subscription Status Values](#subscription-status-values)
- [Error Responses](#error-responses)
- [Example Workflows](#example-workflows)

---

## Base URL

```txt
http://34.229.94.175:8000
```

**API Version:** All billing endpoints are under `/api/v1/billing/`

## Authentication

All billing endpoints require JWT authentication via the `Authorization` header:

```txt
Authorization: Bearer <access_token>
```

Tokens are obtained through the login or register endpoints.

---

## CORS Testing

All endpoints support CORS (Cross-Origin Resource Sharing) for browser-based requests. For testing CORS headers, you can include an optional `Origin` header in your requests:

**Optional Header:**

- `Origin: http://localhost:3000` (or your frontend origin)

**Expected CORS Response Headers:**

- `Access-Control-Allow-Origin: http://localhost:3000` (matches the Origin header)
- `Access-Control-Allow-Credentials: true`
- `Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS, PATCH`
- `Access-Control-Allow-Headers: *`
- `Access-Control-Max-Age: 3600`

**Note:** The Origin header is optional and only needed when testing CORS behavior. The API automatically handles CORS preflight (OPTIONS) requests.

---

## Credit Deduction System

Credits are automatically deducted after successful operations:

- **SuperAdmin & Admin**: Unlimited credits (no deduction)
- **FreeUser & ProUser**: Credits are deducted after successful operations:
  - **LinkedIn search**: 1 credit per search request
  - **LinkedIn export**: 1 credit per LinkedIn URL exported
  - **Email search**: 1 credit per search request
  - **Email export**: 1 credit per contact exported
  - **Contact export**: 1 credit per contact UUID exported
  - **Company export**: 1 credit per company UUID exported

**Important Notes:**

- Credits are deducted **after** successful operation completion
- Negative credit balances are allowed (credits can go below 0)
- Failed operations do not deduct credits
- Export credits are deducted when the export is queued (based on number of items in request)

---

## Billing Endpoints

### GET /api/v1/billing/ - Get Billing Information

Get billing information for the currently authenticated user, including credits, subscription status, and usage information.

**Headers:**

- `Authorization: Bearer <access_token>` (required)

**Response:**

**Success (200 OK):**

```json
{
  "credits": 850,
  "credits_used": 150,
  "credits_limit": 1000,
  "subscription_plan": "5k",
  "subscription_period": "monthly",
  "subscription_status": "active",
  "subscription_started_at": "2024-01-15T10:30:00Z",
  "subscription_ends_at": "2024-02-15T10:30:00Z",
  "usage_percentage": 15.0
}
```

**Response Fields:**

- `credits` (integer): Current credit balance available to the user
- `credits_used` (integer): Number of credits used this billing period
- `credits_limit` (integer): Total credits available per billing period based on current plan
- `subscription_plan` (string): Current subscription plan tier (e.g., "5k", "25k", "100k", "500k", "1M", "5M", "10M")
- `subscription_period` (string, optional): Current subscription billing period. Possible values: `monthly`, `quarterly`, `yearly`
- `subscription_status` (string): Subscription status. Possible values: `active`, `cancelled`, `expired`
- `subscription_started_at` (datetime, ISO 8601, optional): When the subscription started
- `subscription_ends_at` (datetime, ISO 8601, optional): When the subscription ends
- `usage_percentage` (float): Percentage of credits used (0-100)

**Error (401 Unauthorized) - Missing Authentication:**

```json
{
  "detail": "Not authenticated"
}
```

**Error (404 Not Found) - User Profile Not Found:**

```json
{
  "detail": "User profile not found"
}
```

**Error (500 Internal Server Error):**

```json
{
  "detail": "Failed to retrieve billing information"
}
```

---

### GET /api/v1/billing/plans/ - Get Subscription Plans

Get a list of all available subscription plans with all billing periods (monthly, quarterly, yearly). This endpoint does not require authentication.

**Response:**

**Success (200 OK):**

```json
{
  "plans": [
    {
      "tier": "5k",
      "name": "5k Credits Tier",
      "category": "STARTER",
      "periods": {
        "monthly": {
          "period": "monthly",
          "credits": 5000,
          "rate_per_credit": 0.002,
          "price": 10.0,
          "savings": null
        },
        "quarterly": {
          "period": "quarterly",
          "credits": 15000,
          "rate_per_credit": 0.0018,
          "price": 27.0,
          "savings": {
            "amount": 3.0,
            "percentage": 10
          }
        },
        "yearly": {
          "period": "yearly",
          "credits": 60000,
          "rate_per_credit": 0.0016,
          "price": 96.0,
          "savings": {
            "amount": 24.0,
            "percentage": 20
          }
        }
      }
    },
    {
      "tier": "25k",
      "name": "25k Credits Tier",
      "category": "STARTER",
      "periods": {
        "monthly": {
          "period": "monthly",
          "credits": 25000,
          "rate_per_credit": 0.0012,
          "price": 30.0,
          "savings": null
        },
        "quarterly": {
          "period": "quarterly",
          "credits": 75000,
          "rate_per_credit": 0.00108,
          "price": 81.0,
          "savings": {
            "amount": 9.0,
            "percentage": 10
          }
        },
        "yearly": {
          "period": "yearly",
          "credits": 300000,
          "rate_per_credit": 0.00096,
          "price": 288.0,
          "savings": {
            "amount": 72.0,
            "percentage": 20
          }
        }
      }
    }
  ]
}
```

**Response Fields:**

- `plans` (array): List of available subscription plans
  - `tier` (string): Plan tier identifier (e.g., "5k", "25k", "100k", "500k", "1M", "5M", "10M")
  - `name` (string): Plan display name
  - `category` (string): Plan category (STARTER, PROFESSIONAL, BUSINESS, ENTERPRISE)
  - `periods` (object): Pricing for all billing periods
    - `monthly` (object): Monthly billing period details
      - `period` (string): Billing period ("monthly")
      - `credits` (integer): Credits included in this period
      - `rate_per_credit` (float): Rate per credit in USD
      - `price` (float): Total price in USD
      - `savings` (object|null): Savings information (null for monthly, includes amount and percentage for quarterly/yearly)
    - `quarterly` (object): Quarterly billing period details (same structure as monthly)
    - `yearly` (object): Yearly billing period details (same structure as monthly)

**Error (500 Internal Server Error):**

```json
{
  "detail": "Failed to retrieve available plans"
}
```

---

### GET /api/v1/billing/addons/ - Get Addon Packages

Get a list of all available addon credit packages. These packages allow users to purchase additional credits on top of their subscription. This endpoint does not require authentication.

**Response:**

**Success (200 OK):**

```json
{
  "packages": [
    {
      "id": "small",
      "name": "Small",
      "credits": 5000,
      "rate_per_credit": 0.002,
      "price": 10.0
    },
    {
      "id": "basic",
      "name": "Basic",
      "credits": 25000,
      "rate_per_credit": 0.0012,
      "price": 30.0
    },
    {
      "id": "standard",
      "name": "Standard",
      "credits": 100000,
      "rate_per_credit": 0.00099,
      "price": 99.0
    },
    {
      "id": "plus",
      "name": "Plus",
      "credits": 500000,
      "rate_per_credit": 0.000398,
      "price": 199.0
    },
    {
      "id": "pro",
      "name": "Pro",
      "credits": 1000000,
      "rate_per_credit": 0.000299,
      "price": 299.0
    },
    {
      "id": "advanced",
      "name": "Advanced",
      "credits": 5000000,
      "rate_per_credit": 0.0001998,
      "price": 999.0
    },
    {
      "id": "premium",
      "name": "Premium",
      "credits": 10000000,
      "rate_per_credit": 0.0001599,
      "price": 1599.0
    }
  ]
}
```

**Response Fields:**

- `packages` (array): List of available addon packages
  - `id` (string): Package identifier (used for purchase)
  - `name` (string): Package display name
  - `credits` (integer): Credits included in this package
  - `rate_per_credit` (float): Rate per credit in USD
  - `price` (float): Total package price in USD

**Error (500 Internal Server Error):**

```json
{
  "detail": "Failed to retrieve addon packages"
}
```

---

### POST /api/v1/billing/subscribe/ - Subscribe to Plan

Subscribe the currently authenticated user to a subscription plan. Requires both a tier and billing period. This is a simplified implementation. In production, you would integrate with a payment processor like Stripe to handle actual payments.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "tier": "5k",
  "period": "monthly"
}
```

**Request Body Fields:**

- `tier` (string, required): Subscription tier to subscribe to. Must be one of: `5k`, `25k`, `100k`, `500k`, `1M`, `5M`, `10M`
- `period` (string, required): Billing period. Must be one of: `monthly`, `quarterly`, `yearly`

**Response:**

**Success (200 OK):**

```json
{
  "message": "Successfully subscribed to 5k Credits Tier (monthly)",
  "subscription_plan": "5k",
  "subscription_period": "monthly",
  "credits": 5000,
  "subscription_ends_at": "2024-02-15T10:30:00Z"
}
```

**Response Fields:**

- `message` (string): Success message
- `subscription_plan` (string): New subscription plan tier
- `subscription_period` (string): Billing period for the subscription
- `credits` (integer): Credits allocated to the user
- `subscription_ends_at` (datetime, ISO 8601, optional): When the subscription ends (calculated based on period: 30 days for monthly, 90 days for quarterly, 365 days for yearly)

**Error (400 Bad Request) - Invalid Tier or Period:**

```json
{
  "detail": "Invalid tier: invalid_tier"
}
```

or

```json
{
  "detail": "Invalid period: invalid_period. Must be one of: monthly, quarterly, yearly"
}
```

**Error (401 Unauthorized) - Missing Authentication:**

```json
{
  "detail": "Not authenticated"
}
```

**Error (404 Not Found) - User Profile Not Found:**

```json
{
  "detail": "User profile not found"
}
```

**Error (500 Internal Server Error):**

```json
{
  "detail": "Failed to subscribe to plan"
}
```

**Notes:**

- Subscribing to a plan sets the user's credits to the plan's credit allocation for the selected period
- The subscription is set to active status
- The subscription end date is calculated based on the period:
  - Monthly: 30 days from subscription date
  - Quarterly: 90 days from subscription date
  - Yearly: 365 days from subscription date
- In production, this endpoint would integrate with a payment processor to handle actual payments

---

### POST /api/v1/billing/addon/ - Purchase Addon Credits

Purchase addon credits for the currently authenticated user. Addon credits are added to the user's existing credit balance and do not affect the subscription plan. This is a simplified implementation. In production, you would integrate with a payment processor like Stripe to handle actual payments.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "package_id": "small"
}
```

**Request Body Fields:**

- `package_id` (string, required): Addon package ID to purchase. Must be one of: `small`, `basic`, `standard`, `plus`, `pro`, `advanced`, `premium`

**Response:**

**Success (200 OK):**

```json
{
  "message": "Successfully purchased 5000 addon credits.",
  "package": "small",
  "credits_added": 5000,
  "total_credits": 10000
}
```

**Response Fields:**

- `message` (string): Success message
- `package` (string): Package ID that was purchased
- `credits_added` (integer): Credits added to the user's account
- `total_credits` (integer): Total credits after the purchase

**Error (400 Bad Request) - Invalid Package ID:**

```json
{
  "detail": "Invalid package ID: invalid_package"
}
```

**Error (401 Unauthorized) - Missing Authentication:**

```json
{
  "detail": "Not authenticated"
}
```

**Error (404 Not Found) - User Profile Not Found:**

```json
{
  "detail": "User profile not found"
}
```

**Error (500 Internal Server Error):**

```json
{
  "detail": "Failed to purchase addon credits"
}
```

**Notes:**

- Addon credits are added to the user's existing credit balance
- The purchase does not affect the user's subscription plan or status
- Credits from addon packages do not expire
- In production, this endpoint would integrate with a payment processor to handle actual payments

---

### POST /api/v1/billing/cancel/ - Cancel Subscription

Cancel the currently authenticated user's subscription. The subscription will remain active until the end of the current billing period.

**Headers:**

- `Authorization: Bearer <access_token>` (required)

**Response:**

**Success (200 OK):**

```json
{
  "message": "Subscription cancelled. You will retain access until the end of your billing period.",
  "subscription_status": "cancelled"
}
```

**Response Fields:**

- `message` (string): Success message
- `subscription_status` (string): Updated subscription status (will be "cancelled")

**Error (400 Bad Request) - Already Cancelled:**

```json
{
  "detail": "Subscription is already cancelled"
}
```

**Error (401 Unauthorized) - Missing Authentication:**

```json
{
  "detail": "Not authenticated"
}
```

**Error (404 Not Found) - User Profile Not Found:**

```json
{
  "detail": "User profile not found"
}
```

**Error (500 Internal Server Error):**

```json
{
  "detail": "Failed to cancel subscription"
}
```

**Notes:**

- Cancelling a subscription does not immediately revoke access
- The user retains access until the end of the current billing period (subscription_ends_at)
- The subscription status is set to "cancelled"
- Credits are not refunded when cancelling

---

### GET /api/v1/billing/invoices/ - Get Invoice History

Get invoice history for the currently authenticated user. Returns a paginated list of invoices with status and amounts.

**Headers:**

- `Authorization: Bearer <access_token>` (required)

**Query Parameters:**

- `limit` (integer, optional, default: 10, min: 1, max: 100): Maximum number of invoices to return
- `offset` (integer, optional, default: 0, min: 0): Number of invoices to skip (for pagination)

**Response:**

**Success (200 OK):**

```json
{
  "invoices": [
    {
      "id": "inv_664198f7_001",
      "amount": 29.99,
      "status": "paid",
      "created_at": "2024-01-15T10:30:00Z",
      "description": "Subscription to starter plan"
    }
  ],
  "total": 1
}
```

**Response Fields:**

- `invoices` (array): List of invoice items
  - `id` (string): Invoice ID
  - `amount` (float): Invoice amount in USD
  - `status` (string): Invoice status. Possible values: `paid`, `pending`, `failed`
  - `created_at` (datetime, ISO 8601): Invoice creation date
  - `description` (string, optional): Invoice description
- `total` (integer): Total number of invoices for the user

**Error (401 Unauthorized) - Missing Authentication:**

```json
{
  "detail": "Not authenticated"
}
```

**Error (404 Not Found) - User Profile Not Found:**

```json
{
  "detail": "User profile not found"
}
```

**Error (500 Internal Server Error):**

```json
{
  "detail": "Failed to retrieve invoices"
}
```

**Notes:**

- This is a simplified implementation. In production, invoices would be fetched from a payment processor
- Currently returns mock invoice data based on the user's subscription
- Pagination is supported via `limit` and `offset` query parameters

---

## Admin Endpoints (Super Admin Only)

All admin endpoints require Super Admin role. These endpoints allow management of subscription plans and addon packages.

### GET /api/v1/billing/admin/plans/ - Get All Subscription Plans (Admin)

Get all subscription plans for admin management, including inactive plans if requested.

**Headers:**

- `Authorization: Bearer <access_token>` (required, Super Admin only)

**Query Parameters:**

- `include_inactive` (boolean, optional): Include inactive plans in the response (default: false)

**Response:**

**Success (200 OK):**

Same structure as `GET /api/v1/billing/plans/` but may include inactive plans if `include_inactive=true`.

**Error (403 Forbidden) - Not Super Admin:**

```json
{
  "detail": "You do not have permission to perform this action. SuperAdmin role required."
}
```

---

### POST /api/v1/billing/admin/plans/ - Create Subscription Plan (Admin)

Create a new subscription plan.

**Headers:**

- `Authorization: Bearer <access_token>` (required, Super Admin only)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "tier": "5k",
  "name": "5k Credits Tier",
  "category": "STARTER"
}
```

**Response:**

**Success (201 Created):**

```json
{
  "message": "Subscription plan created successfully",
  "tier": "5k"
}
```

---

### PUT /api/v1/billing/admin/plans/{tier}/ - Update Subscription Plan (Admin)

Update an existing subscription plan.

**Headers:**

- `Authorization: Bearer <access_token>` (required, Super Admin only)
- `Content-Type: application/json`

**Path Parameters:**

- `tier` (string): Plan tier identifier (e.g., "5k", "25k")

**Request Body:**

```json
{
  "name": "Updated Plan Name",
  "category": "PROFESSIONAL"
}
```

All fields are optional - only provided fields will be updated.

**Response:**

**Success (200 OK):**

```json
{
  "message": "Subscription plan updated successfully",
  "tier": "5k"
}
```

---

### DELETE /api/v1/billing/admin/plans/{tier}/ - Delete Subscription Plan (Admin)

Delete a subscription plan.

**Headers:**

- `Authorization: Bearer <access_token>` (required, Super Admin only)

**Path Parameters:**

- `tier` (string): Plan tier identifier to delete

**Response:**

**Success (200 OK):**

```json
{
  "message": "Subscription plan deleted successfully",
  "tier": "5k"
}
```

---

### POST /api/v1/billing/admin/plans/{tier}/periods/ - Create/Update Subscription Plan Period (Admin)

Create or update a subscription plan period (monthly, quarterly, or yearly).

**Headers:**

- `Authorization: Bearer <access_token>` (required, Super Admin only)
- `Content-Type: application/json`

**Path Parameters:**

- `tier` (string): Plan tier identifier

**Request Body:**

```json
{
  "period": "monthly",
  "credits": 5000,
  "rate_per_credit": 0.002,
  "price": 10.0,
  "savings_amount": null,
  "savings_percentage": null
}
```

**Response:**

**Success (200 OK):**

```json
{
  "message": "Period created/updated successfully",
  "tier": "5k",
  "period": "monthly"
}
```

---

### DELETE /api/v1/billing/admin/plans/{tier}/periods/{period}/ - Delete Subscription Plan Period (Admin)

Delete a subscription plan period.

**Headers:**

- `Authorization: Bearer <access_token>` (required, Super Admin only)

**Path Parameters:**

- `tier` (string): Plan tier identifier
- `period` (string): Period to delete (monthly, quarterly, or yearly)

**Response:**

**Success (200 OK):**

```json
{
  "message": "Period deleted successfully",
  "tier": "5k",
  "period": "monthly"
}
```

---

### GET /api/v1/billing/admin/addons/ - Get All Addon Packages (Admin)

Get all addon packages for admin management, including inactive packages if requested.

**Headers:**

- `Authorization: Bearer <access_token>` (required, Super Admin only)

**Query Parameters:**

- `include_inactive` (boolean, optional): Include inactive packages in the response (default: false)

**Response:**

**Success (200 OK):**

Same structure as `GET /api/v1/billing/addons/` but may include inactive packages if `include_inactive=true`.

---

### POST /api/v1/billing/admin/addons/ - Create Addon Package (Admin)

Create a new addon package.

**Headers:**

- `Authorization: Bearer <access_token>` (required, Super Admin only)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "id": "small",
  "name": "Small",
  "credits": 5000,
  "rate_per_credit": 0.002,
  "price": 10.0
}
```

**Response:**

**Success (201 Created):**

```json
{
  "message": "Addon package created successfully",
  "id": "small"
}
```

---

### PUT /api/v1/billing/admin/addons/{package_id}/ - Update Addon Package (Admin)

Update an existing addon package.

**Headers:**

- `Authorization: Bearer <access_token>` (required, Super Admin only)
- `Content-Type: application/json`

**Path Parameters:**

- `package_id` (string): Package identifier (e.g., "small", "basic")

**Request Body:**

```json
{
  "name": "Updated Package Name",
  "credits": 6000,
  "rate_per_credit": 0.0018,
  "price": 10.8
}
```

All fields are optional - only provided fields will be updated.

**Response:**

**Success (200 OK):**

```json
{
  "message": "Addon package updated successfully",
  "id": "small"
}
```

---

### DELETE /api/v1/billing/admin/addons/{package_id}/ - Delete Addon Package (Admin)

Delete an addon package.

**Headers:**

- `Authorization: Bearer <access_token>` (required, Super Admin only)

**Path Parameters:**

- `package_id` (string): Package identifier to delete

**Response:**

**Success (200 OK):**

```json
{
  "message": "Addon package deleted successfully",
  "id": "small"
}
```

---

## Subscription Plans

The following subscription plans are available with multiple billing periods (monthly, quarterly, yearly):

### 5k Credits Tier (STARTER)

- **Tier:** `5k`
- **Monthly:** $10.00/month - 5,000 credits ($0.002 per credit)
- **Quarterly:** $27.00/quarter - 15,000 credits ($0.0018 per credit) - Save 10%
- **Yearly:** $96.00/year - 60,000 credits ($0.0016 per credit) - Save 20%

### 25k Credits Tier (STARTER)

- **Tier:** `25k`
- **Monthly:** $30.00/month - 25,000 credits ($0.0012 per credit)
- **Quarterly:** $81.00/quarter - 75,000 credits ($0.00108 per credit) - Save 10%
- **Yearly:** $288.00/year - 300,000 credits ($0.00096 per credit) - Save 20%

### 100k Credits Tier (PROFESSIONAL)

- **Tier:** `100k`
- **Monthly:** $99.00/month - 100,000 credits ($0.00099 per credit)
- **Quarterly:** $267.00/quarter - 300,000 credits ($0.000891 per credit) - Save 10%
- **Yearly:** $950.00/year - 1,200,000 credits ($0.000792 per credit) - Save 20%

### 500k Credits Tier (PROFESSIONAL)

- **Tier:** `500k`
- **Monthly:** $199.00/month - 500,000 credits ($0.000398 per credit)
- **Quarterly:** $537.00/quarter - 1,500,000 credits ($0.0003582 per credit) - Save 10%
- **Yearly:** $1,910.00/year - 6,000,000 credits ($0.0003184 per credit) - Save 20%

### 1M Credits Tier (BUSINESS)

- **Tier:** `1M`
- **Monthly:** $299.00/month - 1,000,000 credits ($0.000299 per credit)
- **Quarterly:** $807.00/quarter - 3,000,000 credits ($0.0002691 per credit) - Save 10%
- **Yearly:** $2,870.00/year - 12,000,000 credits ($0.0002392 per credit) - Save 20%

### 5M Credits Tier (BUSINESS)

- **Tier:** `5M`
- **Monthly:** $999.00/month - 5,000,000 credits ($0.0001998 per credit)
- **Quarterly:** $2,697.00/quarter - 15,000,000 credits ($0.00017982 per credit) - Save 10%
- **Yearly:** $9,590.00/year - 60,000,000 credits ($0.00015984 per credit) - Save 20%

### 10M Credits Tier (ENTERPRISE)

- **Tier:** `10M`
- **Monthly:** $1,599.00/month - 10,000,000 credits ($0.0001599 per credit)
- **Quarterly:** $4,317.00/quarter - 30,000,000 credits ($0.00014391 per credit) - Save 10%
- **Yearly:** $15,350.00/year - 120,000,000 credits ($0.00012792 per credit) - Save 20%

**Note:** All plans include access to all features. The difference is in the credit allocation and pricing. Quarterly and yearly plans offer savings compared to monthly billing.

---

## Addon Packages

Addon packages allow users to purchase additional credits on top of their subscription. These are one-time purchases that add credits to the user's existing balance:

### Small Package

- **ID:** `small`
- **Price:** $10.00
- **Credits:** 5,000
- **Rate:** $0.002 per credit

### Basic Package

- **ID:** `basic`
- **Price:** $30.00
- **Credits:** 25,000
- **Rate:** $0.0012 per credit

### Standard Package

- **ID:** `standard`
- **Price:** $99.00
- **Credits:** 100,000
- **Rate:** $0.00099 per credit

### Plus Package

- **ID:** `plus`
- **Price:** $199.00
- **Credits:** 500,000
- **Rate:** $0.000398 per credit

### Pro Package

- **ID:** `pro`
- **Price:** $299.00
- **Credits:** 1,000,000
- **Rate:** $0.000299 per credit

### Advanced Package

- **ID:** `advanced`
- **Price:** $999.00
- **Credits:** 5,000,000
- **Rate:** $0.0001998 per credit

### Premium Package

- **ID:** `premium`
- **Price:** $1,599.00
- **Credits:** 10,000,000
- **Rate:** $0.0001599 per credit

**Note:** Addon credits are added to the user's existing balance and do not expire. They can be purchased at any time regardless of subscription status.

---

## Subscription Status Values

The following subscription status values are supported:

- `active`: Subscription is active and user has access
- `cancelled`: Subscription has been cancelled but user retains access until end of billing period
- `expired`: Subscription has expired and user no longer has access

---

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request

Returned when request parameters are invalid:

```json
{
  "detail": "Invalid plan ID: invalid_plan"
}
```

### 401 Unauthorized

Returned when authentication is missing or invalid:

```json
{
  "detail": "Not authenticated"
}
```

### 404 Not Found

Returned when the user profile is not found:

```json
{
  "detail": "User profile not found"
}
```

### 500 Internal Server Error

Returned when an unexpected server error occurs:

```json
{
  "detail": "Failed to retrieve billing information"
}
```

---

## Example Workflows

### Workflow 1: Check Billing Information

1. **Get billing information:**

   ```bash
   GET /api/v1/billing/
   Authorization: Bearer <access_token>
   ```

2. **Response:**

   ```json
   {
     "credits": 850,
     "credits_used": 150,
     "credits_limit": 1000,
     "subscription_plan": "5k",
     "subscription_status": "active",
     "usage_percentage": 15.0
   }
   ```

### Workflow 2: Subscribe to a Plan

1. **Get available subscription plans:**

   ```bash
   GET /api/v1/billing/plans/
   ```

2. **Subscribe to a plan:**

   ```bash
   POST /api/v1/billing/subscribe/
   Authorization: Bearer <access_token>
   Content-Type: application/json
   
   {
     "tier": "100k",
     "period": "monthly"
   }
   ```

3. **Response:**

   ```json
   {
     "message": "Successfully subscribed to 100k Credits Tier (monthly)",
     "subscription_plan": "100k",
     "subscription_period": "monthly",
     "credits": 100000,
     "subscription_ends_at": "2024-02-15T10:30:00Z"
   }
   ```

### Workflow 3: Purchase Addon Credits

1. **Get available addon packages:**

   ```bash
   GET /api/v1/billing/addons/
   ```

2. **Purchase addon credits:**

   ```bash
   POST /api/v1/billing/addon/
   Authorization: Bearer <access_token>
   Content-Type: application/json
   
   {
     "package_id": "standard"
   }
   ```

3. **Response:**

   ```json
   {
     "message": "Successfully purchased 100000 addon credits.",
     "package": "standard",
     "credits_added": 100000,
     "total_credits": 200000
   }
   ```

### Workflow 4: Cancel Subscription

### Workflow 3: Cancel Subscription

1. **Cancel subscription:**

   ```bash
   POST /api/v1/billing/cancel/
   Authorization: Bearer <access_token>
   ```

2. **Response:**

   ```json
   {
     "message": "Subscription cancelled. You will retain access until the end of your billing period.",
     "subscription_status": "cancelled"
   }
   ```

### Workflow 5: View Invoice History

1. **Get invoices:**

   ```bash
   GET /api/v1/billing/invoices/?limit=10&offset=0
   Authorization: Bearer <access_token>
   ```

2. **Response:**

   ```json
   {
     "invoices": [
       {
         "id": "inv_664198f7_001",
         "amount": 29.99,
         "status": "paid",
         "created_at": "2024-01-15T10:30:00Z",
         "description": "Subscription to starter plan"
       }
     ],
     "total": 1
   }
   ```

---

## Notes

- All billing endpoints require JWT authentication except `/api/v1/billing/plans/` and `/api/v1/billing/addons/`
- Credits are set to the plan's credit allocation when subscribing to a new plan
- Subscription end dates are calculated based on the billing period:
  - Monthly: 30 days from subscription date
  - Quarterly: 90 days from subscription date
  - Yearly: 365 days from subscription date
- Quarterly and yearly plans offer savings compared to monthly billing (10% and 20% respectively)
- Addon credits are added to the existing balance and do not expire
- Cancelled subscriptions remain active until the end of the billing period
- Invoice data is currently mock data. In production, this would be fetched from a payment processor
- The subscription and addon purchase implementations are simplified. In production, you would integrate with a payment processor like Stripe
