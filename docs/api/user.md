# User API Documentation

Complete API documentation for user authentication and profile management endpoints.

## Base URL

```txt
http://54.87.173.234:8000
```

## Authentication

Most endpoints require JWT authentication via the `Authorization` header:

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

## Authentication Endpoints

### POST /api/v2/auth/register/ - User Registration

Register a new user account and receive access tokens.

**Headers:**

- `Content-Type: application/json`

**Request Body:**

```json
{
  "name": "John Doe",
  "email": "user@example.com",
  "password": "password123"
}
```

**Field Requirements:**

- `name` (string, required): User's full name (max 255 characters)
- `email` (string, required): Valid email address (must be unique, validated using EmailStr)
- `password` (string, required): Password with minimum 8 characters and maximum 72 characters (bcrypt limitation)

**Response:**

**Success (201 Created):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
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

- A user profile is automatically created upon registration
- The email is used as the username
- Tokens are immediately returned for automatic login after registration

---

### POST /api/v2/auth/login/ - User Login

Authenticate a user and receive access tokens.

**Headers:**

- `Content-Type: application/json`

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Field Requirements:**

- `email` (string, required): User's email address
- `password` (string, required): User's password

**Response:**

**Success (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
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

---

### POST /api/v2/auth/logout/ - User Logout

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

### GET /api/v2/auth/session/ - Get Current Session

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
    "id": "123e4567-e89b-12d3-a456-426614174000",
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

### POST /api/v2/auth/refresh/ - Refresh Access Token

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

### GET /api/v2/users/profile/ - Get Current User Profile

Get the profile information for the currently authenticated user.

**Headers:**

- `Authorization: Bearer <access_token>` (required)

**Query Parameters:**

- None

**Response:**

**Success (200 OK):**

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "John Doe",
  "email": "user@example.com",
  "role": "Member",
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

### PUT /api/v2/users/profile/ - Update Current User Profile

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
  "id": "123e4567-e89b-12d3-a456-426614174000",
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

### POST /api/v2/users/profile/avatar/ - Upload User Avatar

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
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "John Doe",
    "email": "user@example.com",
    "role": "Member",
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

### POST /api/v2/users/promote-to-admin/ - Promote User to Admin

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
  "id": "123e4567-e89b-12d3-a456-426614174000",
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
  - `role`: "Member"
  - `notifications`: `{"weeklyReports": true, "newLeadAlerts": true}`
- Token refresh implements token rotation (new tokens issued, old tokens remain valid until expiration)
- The `email` field in the profile is read-only and synced from the User model
- Avatar uploads validate both file extension and file content (magic bytes) for security
- Password hashing uses bcrypt with automatic salt generation
- Password length is limited to 72 characters due to bcrypt's internal limitation
- FastAPI automatically validates request data using Pydantic schemas, returning 422 status for validation errors
- The base URL in examples (`http://54.87.173.234:8000`) is environment-specific and should be replaced with your actual API base URL
