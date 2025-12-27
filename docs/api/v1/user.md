# User API Documentation

Complete API documentation for user authentication and profile management endpoints.

**Related Documentation:**
- [Contacts API](./contacts.md) - For contact management endpoints
- [Companies API](./company.md) - For company management endpoints
- [Apollo API](./apollo.md) - For Apollo URL analysis endpoints
- [Usage API](./usage.md) - For feature usage tracking endpoints

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [Role-Based Access Control](#role-based-access-control)
- [CORS Testing](#cors-testing)
- [Authentication Endpoints](#authentication-endpoints)
  - [POST /api/v1/auth/register](#post-apiv1authregister---user-registration)
  - [POST /api/v1/auth/register/](#post-apiv1authregister---user-registration-with-trailing-slash)
  - [POST /api/v1/auth/login/](#post-apiv1authlogin---user-login)
  - [POST /api/v1/auth/logout/](#post-apiv1authlogout---user-logout)
  - [GET /api/v1/auth/session/](#get-apiv1authsession---get-current-session)
  - [GET /api/v1/auth/user-info/](#get-apiv1authuser-info---get-combined-user-information)
  - [POST /api/v1/auth/refresh/](#post-apiv1authrefresh---refresh-access-token)
- [User Profile Endpoints](#user-profile-endpoints)
  - [GET /api/v1/users/profile/](#get-apiv1usersprofile---get-current-user-profile)
  - [PUT /api/v1/users/profile/](#put-apiv1usersprofile---update-current-user-profile)
  - [POST /api/v1/users/profile/avatar/](#post-apiv1usersprofileavatar---upload-user-avatar)
  - [POST /api/v1/users/promote-to-admin/](#post-apiv1userspromote-to-admin---promote-user-to-admin)
  - [POST /api/v1/users/promote-to-super-admin/](#post-apiv1userspromote-to-super-admin---promote-user-to-super-admin)
- [Super Admin Endpoints](#super-admin-endpoints)
  - [GET /api/v1/users/](#get-apiv1users---list-all-users)
  - [PUT /api/v1/users/{user_id}/role/](#put-apiv1usersuser_idrole---update-user-role)
  - [PUT /api/v1/users/{user_id}/credits/](#put-apiv1usersuser_idcredits---update-user-credits)
  - [DELETE /api/v1/users/{user_id}/](#delete-apiv1usersuser_id---delete-user)
  - [GET /api/v1/users/stats/](#get-apiv1usersstats---get-user-statistics)
  - [GET /api/v1/users/history/](#get-apiv1usershistory---get-user-history)
- [User Scraping Endpoints](#user-scraping-endpoints)
  - [GET /api/v1/users/sales-navigator/list](#get-apiv1userssales-navigatorlist---list-user-scraping-records)
- [Error Responses](#error-responses)
- [Notes](#notes)

---

## Base URL

```txt
http://54.87.173.234:8000
```

**API Version:** 
- Authentication endpoints: `/api/v1/auth/`
- User profile endpoints: `/api/v1/users/`

## Authentication

Most endpoints require JWT authentication via the `Authorization` header:

```txt
Authorization: Bearer <access_token>
```

Tokens are obtained through the login or register endpoints.

---

## Role-Based Access Control

The API implements a comprehensive role-based access control (RBAC) system with four distinct user roles:

### User Roles

1. **SuperAdmin** (`SuperAdmin`)
   - Full control over all users, UI, and plan details
   - Can manage user roles, credits, and delete users
   - Can view user statistics
   - Has access to all features
   - **Unlimited credits** (no credit deduction for any operations)

2. **Admin** (`Admin`)
   - Full control over all UI pages
   - Cannot manage users (no user management capabilities)
   - Can view user statistics
   - Has access to all features
   - **Unlimited credits** (no credit deduction for any operations)

3. **ProUser** (`ProUser`)
   - Full CRUD access to contacts and companies
   - Can purchase subscription plans
   - Has access to all UI features
   - Can modify (update/delete) resources
   - Credits are deducted for operations (1 credit per search, 1 credit per item exported)

4. **FreeUser** (`FreeUser`)
   - Default role for new registrations
   - Receives 50 initial credits upon registration
   - Can create and read contacts and companies
   - Cannot update or delete resources (read-only for modifications)
   - Has access to contact page, company page, LinkedIn, email, and AI assistants
   - Credits are deducted for operations (1 credit per search, 1 credit per item exported)

### Role Permissions Summary

| Action | FreeUser | ProUser | Admin | SuperAdmin |
|--------|----------|---------|-------|------------|
| Create contacts/companies | ✅ | ✅ | ✅ | ✅ |
| Read contacts/companies | ✅ | ✅ | ✅ | ✅ |
| Update contacts/companies | ❌ | ✅ | ✅ | ✅ |
| Delete contacts/companies | ❌ | ✅ | ✅ | ✅ |
| Purchase plans | ❌ | ✅ | ✅ | ✅ |
| Manage users | ❌ | ❌ | ❌ | ✅ |
| View user statistics | ❌ | ❌ | ✅ | ✅ |
| All UI features | ❌ | ✅ | ✅ | ✅ |

### Role Assignment

- **New Registrations**: Automatically assigned `FreeUser` role with 50 initial credits
- **Role Changes**: Only SuperAdmin can change user roles via `PUT /api/v1/users/{user_id}/role/`
- **Self-Promotion**: Users can self-promote to Admin via `POST /api/v1/users/promote-to-admin/` (not recommended for production)

### Error Responses for Role Restrictions

When a user attempts to access an endpoint without the required role, they will receive:

**Error (403 Forbidden):**

```json
{
  "detail": "You do not have permission to perform this action. [Role] role required."
}
```

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

## Authentication Endpoints

### POST /api/v1/auth/register - User Registration

Register a new user account and receive access tokens. This endpoint accepts requests with or without a trailing slash.

**Note:** Both `/api/v1/auth/register` and `/api/v1/auth/register/` are supported for backward compatibility.

**Headers:**

- `Content-Type: application/json`

**Request Body:**

```json
{
  "name": "John Doe",
  "email": "user@example.com",
  "password": "password123",
  "geolocation": {
    "ip": "205.254.184.116",
    "continent": "Asia",
    "continent_code": "AS",
    "country": "India",
    "country_code": "IN",
    "region": "KA",
    "region_name": "Karnataka",
    "city": "Bengaluru",
    "district": "",
    "zip": "",
    "lat": 12.9715,
    "lon": 77.5945,
    "timezone": "Asia/Kolkata",
    "offset": 19800,
    "currency": "INR",
    "isp": "Excitel Broadband Pvt Ltd",
    "org": "Excitel Broadband Pvt Ltd",
    "asname": "",
    "reverse": "",
    "device": "Mozilla/5.0...",
    "proxy": false,
    "hosting": false
  }
}
```

**Field Requirements:**

- `name` (string, required): User's full name (max 255 characters)
- `email` (string, required): Valid email address (must be unique, validated using EmailStr)
- `password` (string, required): Password with minimum 8 characters and maximum 72 characters (bcrypt limitation)
- `geolocation` (object, optional): IP geolocation data from frontend. All fields within geolocation are optional:
  - `ip` (string, optional): IP address
  - `continent` (string, optional): Continent name
  - `continent_code` (string, optional): Two-letter continent code
  - `country` (string, optional): Country name
  - `country_code` (string, optional): Two-letter country code
  - `region` (string, optional): Region code
  - `region_name` (string, optional): Region name
  - `city` (string, optional): City name
  - `district` (string, optional): District name
  - `zip` (string, optional): ZIP/postal code
  - `lat` (number, optional): Latitude
  - `lon` (number, optional): Longitude
  - `timezone` (string, optional): Timezone (e.g., "Asia/Kolkata")
  - `offset` (integer, optional): UTC offset in seconds
  - `currency` (string, optional): Currency code
  - `isp` (string, optional): ISP name
  - `org` (string, optional): Organization name
  - `asname` (string, optional): AS name
  - `reverse` (string, optional): Reverse DNS
  - `device` (string, optional): User-Agent string
  - `proxy` (boolean, optional): Whether IP is a proxy
  - `hosting` (boolean, optional): Whether IP is hosting

**Response:**

**Success (201 Created):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "uuid": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com"
  },
  "message": "Registration successful! Please check your email to verify your account."
}
```

**Error (400 Bad Request) - Email Already Exists:**

```json
{
  "email": ["Email already exists"]
}
```

**Error (400 Bad Request) - Invalid Password:**

```json
{
  "password": [
    "This password is too short. It must contain at least 8 characters."
  ]
}
```

**Error (400 Bad Request) - Password Too Long:**

```json
{
  "password": [
    "String should have at most 72 characters"
  ]
}
```

**Error (422 Unprocessable Entity) - Missing Required Fields:**

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "name"],
      "msg": "Field required",
      "input": {}
    },
    {
      "type": "missing",
      "loc": ["body", "email"],
      "msg": "Field required",
      "input": {}
    },
    {
      "type": "missing",
      "loc": ["body", "password"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

**Error (400 Bad Request) - Invalid Email Format:**

```json
{
  "email": [
    {
      "type": "value_error",
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "input": "invalid-email"
    }
  ]
}
```

Note: FastAPI/Pydantic returns detailed validation errors. The exact format may vary.

**Status Codes:**

- `201 Created`: Registration successful
- `400 Bad Request`: Email already exists or password validation failed (business logic errors)
- `422 Unprocessable Entity`: Invalid request data format or missing required fields (validation errors)

**Notes:**

- A user profile is automatically created upon registration with default values:
  - `role`: `FreeUser` (default role for new users)
  - `credits`: `50` (initial credits for free users)
  - `subscription_plan`: `free`
  - `subscription_status`: `active`
  - `notifications`: `{"weeklyReports": true, "newLeadAlerts": true}`
- The email is used as the username
- Tokens are immediately returned for automatic login after registration
- The `geolocation` field is optional. If provided, it will be stored in the user history table for audit purposes. If not provided, registration will still succeed without geolocation data.
- Geolocation data is typically fetched by the frontend from external APIs (`api64.ipify.org` for IP and `ip-api.com` for geolocation) before sending the registration request.

---

### POST /api/v1/auth/register/ - User Registration (with trailing slash)

Same as `/api/v1/auth/register` but with a trailing slash. Both endpoints are supported for backward compatibility.

---

### POST /api/v1/auth/login/ - User Login

Authenticate a user and receive access tokens.

**Headers:**

- `Content-Type: application/json`

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "password123",
  "geolocation": {
    "ip": "205.254.184.116",
    "continent": "Asia",
    "continent_code": "AS",
    "country": "India",
    "country_code": "IN",
    "region": "KA",
    "region_name": "Karnataka",
    "city": "Bengaluru",
    "district": "",
    "zip": "",
    "lat": 12.9715,
    "lon": 77.5945,
    "timezone": "Asia/Kolkata",
    "offset": 19800,
    "currency": "INR",
    "isp": "Excitel Broadband Pvt Ltd",
    "org": "Excitel Broadband Pvt Ltd",
    "asname": "",
    "reverse": "",
    "device": "Mozilla/5.0...",
    "proxy": false,
    "hosting": false
  }
}
```

**Field Requirements:**

- `email` (string, required): User's email address
- `password` (string, required): User's password
- `geolocation` (object, optional): IP geolocation data from frontend. All fields within geolocation are optional (see register endpoint for field descriptions)

**Response:**

**Success (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "uuid": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com"
  }
}
```

**Error (400 Bad Request) - Invalid Credentials:**

```json
{
  "detail": "Invalid email or password"
}
```

**Error (422 Unprocessable Entity) - Missing Fields:**

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "email"],
      "msg": "Field required",
      "input": {}
    },
    {
      "type": "missing",
      "loc": ["body", "password"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

Note: FastAPI returns 422 for validation errors with detailed field information.

**Error (400 Bad Request) - Account Disabled:**

```json
{
  "detail": {
    "non_field_errors": ["User account is disabled"]
  }
}
```

Note: The actual response format may be a dictionary with `non_field_errors` key or a simple string `detail` field.

**Status Codes:**

- `200 OK`: Login successful
- `400 Bad Request`: Invalid credentials or account disabled
- `422 Unprocessable Entity`: Missing required fields or invalid data format

**Notes:**

- The user's `last_sign_in_at` timestamp is updated upon successful login
- Tokens are generated using JWT (JSON Web Tokens) with HS256 algorithm
- Access tokens expire after 30 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- Refresh tokens expire after 7 days (configurable via `REFRESH_TOKEN_EXPIRE_DAYS`)
- The `geolocation` field is optional. If provided, it will be stored in the user history table for audit purposes. If not provided, login will still succeed without geolocation data.
- Geolocation data is typically fetched by the frontend from external APIs (`api64.ipify.org` for IP and `ip-api.com` for geolocation) before sending the login request.

---

### POST /api/v1/auth/logout/ - User Logout

Logout the current user and invalidate refresh token.

**Headers:**

- `Authorization: Bearer <access_token>` (required)

**Request Body:**

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Field Requirements:**

- `refresh_token` (string, optional): Refresh token to blacklist. If not provided, logout still succeeds but token may not be invalidated.

**Response:**

**Success (200 OK):**

```json
{
  "message": "Logout successful"
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Error (401 Unauthorized) - Invalid Token:**

```json
{
  "detail": "Given token not valid for any token type"
}
```

**Status Codes:**

- `200 OK`: Logout successful
- `401 Unauthorized`: Authentication required or invalid token

**Notes:**

- The refresh token (if provided) is added to a blacklist to prevent reuse
- Access tokens cannot be blacklisted but will expire naturally
- Logout succeeds even if refresh token is invalid or not provided

---

### GET /api/v1/auth/session/ - Get Current Session

Get the current authenticated user's session information.

**Headers:**

- `Authorization: Bearer <access_token>` (required)

**Query Parameters:**

- None

**Response:**

**Success (200 OK):**

```json
{
  "user": {
    "uuid": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "last_sign_in_at": "2024-01-15T12:00:00Z"
  }
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Error (401 Unauthorized) - Invalid Token:**

```json
{
  "detail": "Given token not valid for any token type"
}
```

**Status Codes:**

- `200 OK`: Session valid
- `401 Unauthorized`: Invalid or expired token

**Notes:**

- `last_sign_in_at` will be `null` if the user has never logged in
- This endpoint is useful for checking token validity
- The timestamp is in ISO 8601 format (UTC)

---

### POST /api/v1/auth/refresh/ - Refresh Access Token

Refresh an expired access token using a refresh token.

**Headers:**

- `Content-Type: application/json`

**Request Body:**

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Field Requirements:**

- `refresh_token` (string, required): Valid refresh token

**Response:**

**Success (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Error (400 Bad Request) - Invalid Refresh Token:**

```json
{
  "detail": "Invalid refresh token"
}
```

**Error (400 Bad Request) - Missing Refresh Token:**

```json
{
  "refresh_token": ["This field is required."]
}
```

**Error (400 Bad Request) - Token Error:**

```json
{
  "detail": "Token is invalid or expired"
}
```

**Status Codes:**

- `200 OK`: Token refreshed successfully
- `400 Bad Request`: Invalid refresh token or missing field

**Notes:**

- A new refresh token is also returned (token rotation)
- The old refresh token is not automatically invalidated - both tokens remain valid until they expire
- This endpoint does not require authentication (uses refresh token instead)
- Token rotation provides better security by limiting the lifetime of refresh tokens

---

## User Profile Endpoints

### GET /api/v1/users/profile/ - Get Current User Profile

Get the profile information for the currently authenticated user.

**Headers:**

- `Authorization: Bearer <access_token>` (required)

**Query Parameters:**

- None

**Response:**

**Success (200 OK):**

```json
{
  "uuid": "123e4567-e89b-12d3-a456-426614174000",
  "name": "John Doe",
  "email": "user@example.com",
  "role": "FreeUser",
  "avatar_url": "https://picsum.photos/seed/123/40/40",
  "is_active": true,
  "job_title": "Software Engineer",
  "bio": "Passionate developer",
  "timezone": "America/New_York",
  "notifications": {
    "weeklyReports": true,
    "newLeadAlerts": true
  },
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Error (401 Unauthorized) - Invalid Token:**

```json
{
  "detail": "Given token not valid for any token type"
}
```

**Status Codes:**

- `200 OK`: Profile retrieved successfully
- `401 Unauthorized`: Authentication required

**Notes:**

- If a profile doesn't exist, it will be automatically created with default values
- The profile is linked to the authenticated user via a one-to-one relationship
- All timestamps are in ISO 8601 format (UTC)

---

### PUT /api/v1/users/profile/ - Update Current User Profile

Update the profile information for the currently authenticated user. All fields are optional - only provided fields will be updated.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "name": "John Doe Updated",
  "job_title": "Senior Software Engineer",
  "bio": "Updated bio",
  "timezone": "America/Los_Angeles",
  "avatar_url": "https://picsum.photos/seed/123/40/40",
  "notifications": {
    "weeklyReports": false,
    "newLeadAlerts": true
  },
  "role": "Admin"
}
```

**Field Requirements:**

All fields are optional:

- `name` (string, optional): User's full name (max 255 characters)
- `job_title` (string, optional): User's job title (max 255 characters)
- `bio` (string, optional): User's biography (text field)
- `timezone` (string, optional): User's timezone (max 100 characters, e.g., "America/New_York")
- `avatar_url` (string, optional): URL to user's avatar image
- `notifications` (object, optional): User notification preferences (merged with existing preferences)
- `role` (string, optional): User's role (max 50 characters)

**Response:**

**Success (200 OK):**

```json
{
  "uuid": "123e4567-e89b-12d3-a456-426614174000",
  "name": "John Doe Updated",
  "email": "user@example.com",
  "role": "Admin",
  "avatar_url": "https://picsum.photos/seed/123/40/40",
  "is_active": true,
  "job_title": "Senior Software Engineer",
  "bio": "Updated bio",
  "timezone": "America/Los_Angeles",
  "notifications": {
    "weeklyReports": false,
    "newLeadAlerts": true
  },
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T12:00:00Z"
}
```

**Error (400 Bad Request) - Invalid Data:**

```json
{
  "detail": "Invalid data provided"
}
```

**Error (400 Bad Request) - Field Validation Errors:**

```json
{
  "name": ["Ensure this field has no more than 255 characters."],
  "timezone": ["Ensure this field has no more than 100 characters."]
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Status Codes:**

- `200 OK`: Profile updated successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required

**Notes:**

- This is a partial update (PATCH-like behavior) - only provided fields are updated
- The `notifications` field is merged with existing preferences, not replaced
- If a profile doesn't exist, it will be automatically created
- The `email` field cannot be updated through this endpoint (it's read-only)
- The `updated_at` timestamp is automatically updated

---

### POST /api/v1/users/profile/avatar/ - Upload User Avatar

Upload an avatar image file for the currently authenticated user. The image will be stored in the media directory and the user's `avatar_url` will be updated automatically.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: multipart/form-data`

**Request Body:**

Form data with a file field named `avatar`:

```txt
avatar: [image file]
```

**File Requirements:**

- **File Types**: JPEG, PNG, GIF, or WebP
- **Maximum Size**: 5MB (5,242,880 bytes)
- **Validation**: Both file extension and file content (magic bytes) are validated
- **Allowed Extensions**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`

**Response:**

**Success (200 OK):**

```json
{
  "avatar_url": "http://54.87.173.234:8000/media/avatars/123e4567-e89b-12d3-a456-426614174000_20240115T120000123456.jpg",
  "profile": {
    "uuid": "123e4567-e89b-12d3-a456-426614174000",
    "name": "John Doe",
    "email": "user@example.com",
    "role": "FreeUser",
    "avatar_url": "http://54.87.173.234:8000/media/avatars/123e4567-e89b-12d3-a456-426614174000_20240115T120000123456.jpg",
    "is_active": true,
    "job_title": "Software Engineer",
    "bio": "Passionate developer",
    "timezone": "America/New_York",
    "notifications": {
      "weeklyReports": true,
      "newLeadAlerts": true
    },
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-15T12:00:00Z"
  },
  "message": "Avatar uploaded successfully"
}
```

Note: The `avatar_url` in the response is a full URL (includes base URL). The file is stored with a relative path in the database.

**Error (400 Bad Request) - File Too Large:**

```json
{
  "avatar": [
    "Image file too large. Maximum size is 5.0MB"
  ]
}
```

**Error (400 Bad Request) - Invalid File Type:**

```json
{
  "avatar": [
    "Invalid file type. Allowed types: .jpg, .jpeg, .png, .gif, .webp"
  ]
}
```

**Error (400 Bad Request) - Invalid Image File:**

```json
{
  "avatar": [
    "File does not appear to be a valid image file"
  ]
}
```

**Error (400 Bad Request) - Missing File:**

```json
{
  "avatar": [
    "This field is required."
  ]
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Error (500 Internal Server Error):**

```json
{
  "detail": "Error saving file: [error message]"
}
```

**Status Codes:**

- `200 OK`: Avatar uploaded successfully
- `400 Bad Request`: Invalid file (wrong type, too large, or not a valid image)
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Server error while saving file

**Notes:**

- The old avatar file (if it exists and is a local file) will be automatically deleted when a new avatar is uploaded
- External avatar URLs (not stored locally, starting with `http://` or `https://`) will not be deleted
- The filename format is: `{user_id}_{timestamp}.{extension}` where timestamp is in format `YYYYMMDDTHHMMSSffffff` (UTC)
- Files are stored in the `uploads/avatars/` directory (configurable via `UPLOAD_DIR` setting)
- File validation checks both extension and magic bytes (file signature) to ensure it's actually an image
- Supported image signatures: JPEG (`\xff\xd8\xff`), PNG (`\x89\x50\x4e\x47`), GIF (`GIF87a` or `GIF89a`), WebP (`RIFF` with `WEBP`)
- If a profile doesn't exist, it will be automatically created with default values
- The avatar URL stored in the database is relative (`/media/avatars/{filename}`), but the API response returns a full URL using the `BASE_URL` configuration

---

### POST /api/v1/users/promote-to-admin/ - Promote User to Admin

Promote the currently authenticated user to admin role. This endpoint allows authenticated users to change their role to "Admin". The operation is logged for audit purposes.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Accept: application/json`

**Request Body:**

No request body required. The endpoint uses the authenticated user from the Bearer token.

**Response:**

**Success (200 OK):**

```json
{
  "uuid": "123e4567-e89b-12d3-a456-426614174000",
  "name": "John Doe",
  "email": "user@example.com",
  "role": "Admin",
  "avatar_url": null,
  "is_active": true,
  "job_title": "Software Engineer",
  "bio": "Passionate developer",
  "timezone": "America/New_York",
  "notifications": {
    "weeklyReports": true,
    "newLeadAlerts": true
  },
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T12:00:00Z"
}
```

**Error (400 Bad Request) - User Account Disabled:**

```json
{
  "non_field_errors": ["User account is disabled"]
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Error (404 Not Found):**

```json
{
  "detail": "User not found"
}
```

**Error (500 Internal Server Error):**

```json
{
  "detail": "Failed to promote user to admin"
}
```

**Status Codes:**

- `200 OK`: User promoted to admin successfully
- `400 Bad Request`: User account is disabled
- `401 Unauthorized`: Authentication required
- `404 Not Found`: User not found
- `500 Internal Server Error`: Server error while promoting user

**Notes:**

- This endpoint allows authenticated users to self-promote to admin role
- The operation is logged for audit purposes (all promotion attempts are recorded)
- If a profile doesn't exist, it will be automatically created with default values before promotion
- The `role` field in the profile is updated to "Admin"
- The `updated_at` timestamp is automatically updated
- This is a self-service endpoint with no additional security checks (consider adding rate limiting or admin approval workflow in production)

---

### POST /api/v1/users/promote-to-super-admin/ - Promote User to Super Admin

Promote a user to super admin role (Super Admin only). This endpoint allows super admins to promote any user to "SuperAdmin" role. The operation is logged for audit purposes.

**Headers:**

- `Authorization: Bearer <access_token>` (required, SuperAdmin role)
- `Accept: application/json`

**Query Parameters:**

- `user_id` (string, UUID, required): User ID to promote to super admin

**Request Body:**

No request body required. The target user UUID is specified via the `user_id` query parameter.

**Response:**

**Success (200 OK):**

```json
{
  "uuid": "123e4567-e89b-12d3-a456-426614174000",
  "name": "John Doe",
  "email": "user@example.com",
  "role": "SuperAdmin",
  "avatar_url": null,
  "is_active": true,
  "job_title": "Software Engineer",
  "bio": "Passionate developer",
  "timezone": "America/New_York",
  "notifications": {
    "weeklyReports": true,
    "newLeadAlerts": true
  },
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T12:00:00Z"
}
```

**Error (400 Bad Request) - User Account Disabled:**

```json
{
  "non_field_errors": ["User account is disabled"]
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Error (403 Forbidden) - Not Super Admin:**

```json
{
  "detail": "You do not have permission to perform this action. SuperAdmin role required."
}
```

**Error (404 Not Found):**

```json
{
  "detail": "User not found"
}
```

**Error (500 Internal Server Error):**

```json
{
  "detail": "Failed to promote user to super admin"
}
```

**Status Codes:**

- `200 OK`: User promoted to super admin successfully
- `400 Bad Request`: User account is disabled
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: SuperAdmin role required
- `404 Not Found`: User not found
- `500 Internal Server Error`: Server error while promoting user

**Notes:**

- Only SuperAdmin can promote users to SuperAdmin role
- The operation is logged for audit purposes (all promotion attempts are recorded)
- If a profile doesn't exist, it will be automatically created with default values before promotion
- The `role` field in the profile is updated to "SuperAdmin"
- The `updated_at` timestamp is automatically updated
- Requires `user_id` query parameter to specify the target user

---

## Super Admin Endpoints

All Super Admin endpoints require the `SuperAdmin` role. These endpoints allow full user management capabilities.

### GET /api/v1/users/ - List All Users

List all users in the system with their profiles. This endpoint is restricted to Super Admin only.

**Headers:**

- `Authorization: Bearer <access_token>` (required, SuperAdmin role)

**Query Parameters:**

- `limit` (integer, optional, default: 100, min: 1, max: 1000): Maximum number of users to return
- `offset` (integer, optional, default: 0, min: 0): Number of users to skip (for pagination)

**Response:**

**Success (200 OK):**

```json
{
  "users": [
    {
      "uuid": "123e4567-e89b-12d3-a456-426614174000",
      "email": "user@example.com",
      "name": "John Doe",
      "role": "FreeUser",
      "is_active": true,
      "credits": 50,
      "subscription_plan": "free",
      "subscription_status": "active",
      "created_at": "2024-01-01T00:00:00Z",
      "last_sign_in_at": "2024-01-15T12:00:00Z"
    }
  ],
  "total": 150
}
```

**Error (403 Forbidden) - Not Super Admin:**

```json
{
  "detail": "You do not have permission to perform this action. SuperAdmin role required."
}
```

**Status Codes:**

- `200 OK`: Users retrieved successfully
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: SuperAdmin role required
- `500 Internal Server Error`: Failed to list users

**Notes:**

- Returns paginated list of all users with their profile information
- Includes role, credits, subscription plan, and status for each user
- Only SuperAdmin can access this endpoint

---

### PUT /api/v1/users/{user_id}/role/ - Update User Role

Update a user's role. This endpoint is restricted to Super Admin only.

**Headers:**

- `Authorization: Bearer <access_token>` (required, SuperAdmin role)
- `Content-Type: application/json`

**Path Parameters:**

- `user_id` (string, UUID, required): User ID to update

**Request Body:**

```json
{
  "role": "ProUser"
}
```

**Field Requirements:**

- `role` (string, required): New role for the user. Valid values: `SuperAdmin`, `Admin`, `FreeUser`, `ProUser`

**Response:**

**Success (200 OK):**

Returns a `ProfileResponse` object with the updated role.

**Error (400 Bad Request) - Invalid Role:**

```json
{
  "detail": "Invalid role: invalid_role. Valid roles: SuperAdmin, Admin, FreeUser, ProUser"
}
```

**Error (403 Forbidden) - Not Super Admin:**

```json
{
  "detail": "You do not have permission to perform this action. SuperAdmin role required."
}
```

**Error (404 Not Found):**

```json
{
  "detail": "User not found"
}
```

**Status Codes:**

- `200 OK`: Role updated successfully
- `400 Bad Request`: Invalid role value
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: SuperAdmin role required
- `404 Not Found`: User not found
- `500 Internal Server Error`: Failed to update user role

**Notes:**

- Only SuperAdmin can change user roles
- Valid roles: `SuperAdmin`, `Admin`, `FreeUser`, `ProUser`
- The operation is logged for audit purposes

---

### PUT /api/v1/users/{user_id}/credits/ - Update User Credits

Update a user's credit balance. This endpoint is restricted to Super Admin only.

**Headers:**

- `Authorization: Bearer <access_token>` (required, SuperAdmin role)
- `Content-Type: application/json`

**Path Parameters:**

- `user_id` (string, UUID, required): User ID to update

**Request Body:**

```json
{
  "credits": 1000
}
```

**Field Requirements:**

- `credits` (integer, required, min: 0): New credit balance for the user

**Response:**

**Success (200 OK):**

Returns a `ProfileResponse` object with the updated credits.

**Error (403 Forbidden) - Not Super Admin:**

```json
{
  "detail": "You do not have permission to perform this action. SuperAdmin role required."
}
```

**Error (404 Not Found):**

```json
{
  "detail": "User not found"
}
```

**Status Codes:**

- `200 OK`: Credits updated successfully
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: SuperAdmin role required
- `404 Not Found`: User not found
- `500 Internal Server Error`: Failed to update user credits

**Notes:**

- Only SuperAdmin can modify user credits
- Credits must be a non-negative integer
- Useful for manual credit adjustments or promotional credits

---

### DELETE /api/v1/users/{user_id}/ - Delete User

Delete a user and their profile. This endpoint is restricted to Super Admin only.

**Headers:**

- `Authorization: Bearer <access_token>` (required, SuperAdmin role)

**Path Parameters:**

- `user_id` (string, UUID, required): User ID to delete

**Response:**

**Success (204 No Content):**

No response body.

**Error (400 Bad Request) - Cannot Delete Self:**

```json
{
  "detail": "Cannot delete your own account"
}
```

**Error (403 Forbidden) - Not Super Admin:**

```json
{
  "detail": "You do not have permission to perform this action. SuperAdmin role required."
}
```

**Error (404 Not Found):**

```json
{
  "detail": "User not found"
}
```

**Status Codes:**

- `204 No Content`: User deleted successfully
- `400 Bad Request`: Cannot delete own account
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: SuperAdmin role required
- `404 Not Found`: User not found
- `500 Internal Server Error`: Failed to delete user

**Notes:**

- Only SuperAdmin can delete users
- Cannot delete your own account (prevents accidental self-deletion)
- This will cascade delete the user's profile and all related data
- This operation cannot be undone

---

### GET /api/v1/users/stats/ - Get User Statistics

Get aggregated statistics about users in the system. This endpoint is restricted to Admin or Super Admin.

**Headers:**

- `Authorization: Bearer <access_token>` (required, Admin or SuperAdmin role)

**Response:**

**Success (200 OK):**

```json
{
  "total_users": 150,
  "active_users": 120,
  "users_by_role": {
    "FreeUser": 100,
    "ProUser": 30,
    "Admin": 15,
    "SuperAdmin": 5
  },
  "users_by_plan": {
    "free": 100,
    "5k": 20,
    "25k": 10,
    "100k": 5
  }
}
```

**Response Fields:**

- `total_users` (integer): Total number of users in the system
- `active_users` (integer): Number of active users (is_active = true)
- `users_by_role` (object): Count of users grouped by role
- `users_by_plan` (object): Count of users grouped by subscription plan

**Error (403 Forbidden) - Not Admin or Super Admin:**

```json
{
  "detail": "Admin or Super Admin role required"
}
```

**Status Codes:**

- `200 OK`: Statistics retrieved successfully
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Admin or SuperAdmin role required
- `500 Internal Server Error`: Failed to get user statistics

**Notes:**

- Both Admin and SuperAdmin can access this endpoint
- Statistics are calculated in real-time from the database
- Useful for dashboard and analytics purposes

---

### GET /api/v1/users/history/ - Get User History

Get user history records (Super Admin only). Returns paginated list of user registration and login events with IP geolocation data. Supports filtering by user_id (UUID format) and event_type.

**Headers:**

- `Authorization: Bearer <access_token>` (required, SuperAdmin role)

**Query Parameters:**

- `user_id` (string, UUID, optional): Filter by user ID (must be valid UUID format)
- `event_type` (string, optional): Filter by event type. Valid values: `registration`, `login`
- `limit` (integer, optional, default: 100, min: 1, max: 1000): Maximum number of records to return
- `offset` (integer, optional, default: 0, min: 0): Number of records to skip (for pagination)

**Response:**

**Success (200 OK):**

```json
{
  "items": [
    {
      "id": 1,
      "user_id": "223e4567-e89b-12d3-a456-426614174001",
      "user_email": "user@example.com",
      "user_name": "John Doe",
      "event_type": "registration",
      "ip": "192.168.1.1",
      "continent": "North America",
      "continent_code": "NA",
      "country": "United States",
      "country_code": "US",
      "region": "CA",
      "region_name": "California",
      "city": "New York",
      "district": "",
      "zip": "10001",
      "lat": 40.7128,
      "lon": -74.0060,
      "timezone": "America/New_York",
      "currency": "USD",
      "isp": "Example ISP",
      "org": "Example Org",
      "device": "Mozilla/5.0...",
      "proxy": false,
      "hosting": false,
      "created_at": "2024-01-01T00:00:00Z"
    },
    {
      "id": 2,
      "user_id": "223e4567-e89b-12d3-a456-426614174001",
      "user_email": "user@example.com",
      "user_name": "John Doe",
      "event_type": "login",
      "ip": "192.168.1.2",
      "continent": "North America",
      "continent_code": "NA",
      "country": "United States",
      "country_code": "US",
      "region": "CA",
      "region_name": "California",
      "city": "San Francisco",
      "district": "",
      "zip": "94102",
      "lat": 37.7749,
      "lon": -122.4194,
      "timezone": "America/Los_Angeles",
      "currency": "USD",
      "isp": "Example ISP",
      "org": "Example Org",
      "device": "Mozilla/5.0...",
      "proxy": false,
      "hosting": false,
      "created_at": "2024-01-15T12:00:00Z"
    }
  ],
  "total": 250,
  "limit": 100,
  "offset": 0
}
```

**Response Fields:**

- `items` (array): List of user history records (UserHistoryItem objects)
  - `id` (integer): History record ID
  - `user_id` (string, UUID): User ID associated with this event
  - `user_email` (string, optional): User email address
  - `user_name` (string, optional): User name
  - `event_type` (string): Event type - `registration` or `login`
  - `ip` (string, optional): IP address from the request
  - `continent` (string, optional): Continent from IP geolocation
  - `continent_code` (string, optional): Two-letter continent code
  - `country` (string, optional): Country from IP geolocation
  - `country_code` (string, optional): Two-letter country code
  - `region` (string, optional): Region code
  - `region_name` (string, optional): Region name
  - `city` (string, optional): City from IP geolocation
  - `district` (string, optional): District name
  - `zip` (string, optional): ZIP/postal code
  - `lat` (float, optional): Latitude
  - `lon` (float, optional): Longitude
  - `timezone` (string, optional): Timezone (e.g., "America/New_York")
  - `currency` (string, optional): Currency code
  - `isp` (string, optional): ISP name
  - `org` (string, optional): Organization name
  - `device` (string, optional): User-Agent string
  - `proxy` (boolean, optional): Whether IP is a proxy
  - `hosting` (boolean, optional): Whether IP is hosting
  - `created_at` (datetime, ISO 8601): When the event occurred
- `total` (integer): Total number of history records matching the filters
- `limit` (integer): Maximum number of records returned
- `offset` (integer): Number of records skipped

**Error (403 Forbidden) - Not Super Admin:**

```json
{
  "detail": "You do not have permission to perform this action. SuperAdmin role required."
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Status Codes:**

- `200 OK`: User history retrieved successfully
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: SuperAdmin role required
- `500 Internal Server Error`: Failed to get user history

**Notes:**

- Only SuperAdmin can access this endpoint
- Returns paginated list of user registration and login events
- Includes IP geolocation data (country, city, IP, ISP, etc.) when available
- Supports filtering by `user_id` (UUID format) and `event_type`
- The `user_id` query parameter must be a valid UUID format if provided
- Events are recorded automatically during registration and login
- IP geolocation data is provided by the frontend in the request body (optional field). If not provided, history records will be created without geolocation data.

---

## User Scraping Endpoints

### GET /api/v1/users/sales-navigator/list - List User Scraping Records

List Sales Navigator scraping records for the authenticated user. Returns a paginated list of scraping metadata records ordered by timestamp (newest first).

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Accept: application/json`

**Query Parameters:**

- `limit` (integer, optional, default: 100, min: 1, max: 1000): Maximum number of records to return
- `offset` (integer, optional, default: 0, min: 0): Number of records to skip (for pagination)

**Response:**

**Success (200 OK):**

```json
{
  "items": [
    {
      "id": 1,
      "user_id": "123e4567-e89b-12d3-a456-426614174000",
      "timestamp": "2024-01-15T10:30:00Z",
      "version": "1.0.0",
      "source": "sales_navigator",
      "search_context": {
        "keywords": "software engineer",
        "location": "San Francisco"
      },
      "pagination": {
        "page": 1,
        "per_page": 25
      },
      "user_info": {
        "user_agent": "Mozilla/5.0...",
        "ip_address": "192.168.1.1"
      },
      "application_info": {
        "version": "1.0.0",
        "platform": "web"
      },
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 50,
  "limit": 100,
  "offset": 0
}
```

**Response Fields:**

- `items` (array): List of user scraping records (UserScrapingResponse objects)
  - `id` (integer): Record ID
  - `user_id` (string, UUID): User ID associated with this scraping record
  - `timestamp` (datetime, ISO 8601): Timestamp when the scraping occurred
  - `version` (string): Version of the scraping system
  - `source` (string): Source of the scraping (e.g., "sales_navigator")
  - `search_context` (object, optional): Search context used for scraping
  - `pagination` (object, optional): Pagination information
  - `user_info` (object, optional): User information (user agent, IP address)
  - `application_info` (object, optional): Application information (version, platform)
  - `created_at` (datetime, ISO 8601): When the record was created
  - `updated_at` (datetime, ISO 8601): When the record was last updated
- `total` (integer): Total number of scraping records for the user
- `limit` (integer): Maximum number of records returned
- `offset` (integer): Number of records skipped

**Error (401 Unauthorized):**

```json
{
  "detail": "Not authenticated"
}
```

**Error (500 Internal Server Error):**

```json
{
  "detail": "Failed to retrieve user scraping records"
}
```

**Status Codes:**

- `200 OK`: Scraping records retrieved successfully
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Failed to retrieve scraping records

**Example Request:**

```bash
curl -X GET "http://54.87.173.234:8000/api/v1/users/sales-navigator/list?limit=50&offset=0" \
  -H "Authorization: Bearer <access_token>" \
  -H "Accept: application/json"
```

**Notes:**

- Only returns scraping records for the currently authenticated user
- Records are ordered by timestamp (newest first)
- Supports pagination via `limit` and `offset` query parameters
- All authenticated users can access their own scraping records
- This endpoint is related to Sales Navigator HTML scraping functionality (see [Scrape API](./scrape.md))

---

## Error Responses

All endpoints may return the following common error responses:

### 400 Bad Request

```json
{
  "detail": "Error message describing what went wrong"
}
```

Or field-specific errors:

```json
{
  "field_name": ["Error message for this field"]
}
```

### 401 Unauthorized

```json
{
  "detail": "Authentication credentials were not provided."
}
```

Or:

```json
{
  "detail": "Given token not valid for any token type"
}
```

### 403 Forbidden

Returned when the user does not have the required role:

```json
{
  "detail": "You do not have permission to perform this action. [Role] role required."
}
```

### 500 Internal Server Error

```json
{
  "detail": "An error occurred while processing the request."
}
```

---

## Notes

- All timestamps are in ISO 8601 format (UTC): `YYYY-MM-DDTHH:MM:SSZ`
- JWT tokens use HS256 algorithm with configurable expiration:
  - Access tokens: 30 minutes (default, configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
  - Refresh tokens: 7 days (default, configurable via `REFRESH_TOKEN_EXPIRE_DAYS`)
- Profile creation happens automatically upon user registration with default values:
  - `role`: `FreeUser` (default role for new users)
  - `credits`: `50` (initial credits for free users)
  - `subscription_plan`: `free`
  - `subscription_status`: `active`
  - `notifications`: `{"weeklyReports": true, "newLeadAlerts": true}`
- Token refresh implements token rotation (new tokens issued, old tokens remain valid until expiration)
- The `email` field in the profile is read-only and synced from the User model
- Avatar uploads validate both file extension and file content (magic bytes) for security
- Password hashing uses bcrypt with automatic salt generation
- Password length is limited to 72 characters due to bcrypt's internal limitation
- FastAPI automatically validates request data using Pydantic schemas, returning 422 status for validation errors
- The base URL in examples (`http://54.87.173.234:8000`) is environment-specific and should be replaced with your actual API base URL
