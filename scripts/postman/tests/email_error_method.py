    def _generate_email_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate email-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body for reference
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Email finder endpoint (GET with query params - handled separately, not here)
        # This method only handles POST endpoints with request bodies
        
        # Email export endpoint error tests
        if endpoint_path == "/api/v3/email/export" and method == "POST":
            if valid_body:
                # Missing required contacts field
                test_cases.append({
                    "name": "missing_required_contacts",
                    "description": "Email export without required contacts field (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": {},
                    "expected_status": [400, 422],
                })
                
                # Empty contacts array
                empty_contacts_body = valid_body.copy()
                empty_contacts_body["contacts"] = []
                test_cases.append({
                    "name": "empty_contacts_array",
                    "description": "Email export with empty contacts array (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_contacts_body,
                    "expected_status": [400, 422],
                })
                
                # Invalid contacts structure (not an array)
                invalid_contacts_body = valid_body.copy()
                invalid_contacts_body["contacts"] = "not-an-array"
                test_cases.append({
                    "name": "invalid_contacts_type",
                    "description": "Email export with invalid contacts type (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_contacts_body,
                    "expected_status": [400, 422],
                })
        
        # Single email endpoint error tests
        if endpoint_path == "/api/v3/email/single/" and method == "POST":
            if valid_body:
                # Missing required first_name
                missing_first_name_body = valid_body.copy()
                missing_first_name_body.pop("first_name", None)
                test_cases.append({
                    "name": "missing_first_name",
                    "description": "Single email without first_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_first_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing required last_name
                missing_last_name_body = valid_body.copy()
                missing_last_name_body.pop("last_name", None)
                test_cases.append({
                    "name": "missing_last_name",
                    "description": "Single email without last_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_last_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing required domain
                missing_domain_body = valid_body.copy()
                missing_domain_body.pop("domain", None)
                test_cases.append({
                    "name": "missing_domain",
                    "description": "Single email without domain (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_domain_body,
                    "expected_status": [400, 422],
                })
                
                # Empty first_name
                empty_first_name_body = valid_body.copy()
                empty_first_name_body["first_name"] = ""
                test_cases.append({
                    "name": "empty_first_name",
                    "description": "Single email with empty first_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_first_name_body,
                    "expected_status": [400],
                })
                
                # Empty last_name
                empty_last_name_body = valid_body.copy()
                empty_last_name_body["last_name"] = ""
                test_cases.append({
                    "name": "empty_last_name",
                    "description": "Single email with empty last_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_last_name_body,
                    "expected_status": [400],
                })
                
                # Empty domain
                empty_domain_body = valid_body.copy()
                empty_domain_body["domain"] = ""
                test_cases.append({
                    "name": "empty_domain",
                    "description": "Single email with empty domain (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_domain_body,
                    "expected_status": [400],
                })
        
        # Bulk verifier endpoint error tests
        if endpoint_path == "/api/v3/email/bulk/verifier/" and method == "POST":
            if valid_body:
                # Missing required provider
                missing_provider_body = valid_body.copy()
                missing_provider_body.pop("provider", None)
                test_cases.append({
                    "name": "missing_provider",
                    "description": "Bulk verifier without provider (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_provider_body,
                    "expected_status": [400, 422],
                })
                
                # Missing required emails
                missing_emails_body = valid_body.copy()
                missing_emails_body.pop("emails", None)
                test_cases.append({
                    "name": "missing_emails",
                    "description": "Bulk verifier without emails array (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_emails_body,
                    "expected_status": [400, 422],
                })
                
                # Empty emails array
                empty_emails_body = valid_body.copy()
                empty_emails_body["emails"] = []
                test_cases.append({
                    "name": "empty_emails_array",
                    "description": "Bulk verifier with empty emails array (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_emails_body,
                    "expected_status": [400, 422],
                })
                
                # Invalid provider value
                invalid_provider_body = valid_body.copy()
                invalid_provider_body["provider"] = "invalid_provider"
                test_cases.append({
                    "name": "invalid_provider",
                    "description": "Bulk verifier with invalid provider (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_provider_body,
                    "expected_status": [400, 422],
                })
        
        # Single verifier endpoint error tests
        if endpoint_path == "/api/v3/email/single/verifier/" and method == "POST":
            if valid_body:
                # Missing required email
                missing_email_body = valid_body.copy()
                missing_email_body.pop("email", None)
                test_cases.append({
                    "name": "missing_email",
                    "description": "Single verifier without email (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_email_body,
                    "expected_status": [400, 422],
                })
                
                # Missing required provider
                missing_provider_body = valid_body.copy()
                missing_provider_body.pop("provider", None)
                test_cases.append({
                    "name": "missing_provider",
                    "description": "Single verifier without provider (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_provider_body,
                    "expected_status": [400, 422],
                })
                
                # Empty email
                empty_email_body = valid_body.copy()
                empty_email_body["email"] = ""
                test_cases.append({
                    "name": "empty_email",
                    "description": "Single verifier with empty email (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_email_body,
                    "expected_status": [400],
                })
                
                # Invalid email format
                invalid_email_body = valid_body.copy()
                invalid_email_body["email"] = "not-an-email"
                test_cases.append({
                    "name": "invalid_email_format",
                    "description": "Single verifier with invalid email format (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_email_body,
                    "expected_status": [400, 422],
                })
                
                # Invalid provider value
                invalid_provider_body = valid_body.copy()
                invalid_provider_body["provider"] = "invalid_provider"
                test_cases.append({
                    "name": "invalid_provider",
                    "description": "Single verifier with invalid provider (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_provider_body,
                    "expected_status": [400, 422],
                })
        
        # Verifier endpoint error tests
        if endpoint_path == "/api/v3/email/verifier/" and method == "POST":
            if valid_body:
                # Missing required fields
                test_cases.append({
                    "name": "missing_required_fields",
                    "description": "Verifier without required fields (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": {},
                    "expected_status": [400, 422],
                })
                
                # Missing first_name
                missing_first_name_body = valid_body.copy()
                missing_first_name_body.pop("first_name", None)
                test_cases.append({
                    "name": "missing_first_name",
                    "description": "Verifier without first_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_first_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing last_name
                missing_last_name_body = valid_body.copy()
                missing_last_name_body.pop("last_name", None)
                test_cases.append({
                    "name": "missing_last_name",
                    "description": "Verifier without last_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_last_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing domain
                missing_domain_body = valid_body.copy()
                missing_domain_body.pop("domain", None)
                test_cases.append({
                    "name": "missing_domain",
                    "description": "Verifier without domain (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_domain_body,
                    "expected_status": [400, 422],
                })
                
                # Invalid email_count (negative or zero)
                if "email_count" in valid_body:
                    invalid_email_count_body = valid_body.copy()
                    invalid_email_count_body["email_count"] = -1
                    test_cases.append({
                        "name": "invalid_email_count_negative",
                        "description": "Verifier with negative email_count (should fail)",
                        "method": method,
                        "endpoint": endpoint_path,
                        "body": invalid_email_count_body,
                        "expected_status": [400, 422],
                    })
                    
                    invalid_email_count_zero_body = valid_body.copy()
                    invalid_email_count_zero_body["email_count"] = 0
                    test_cases.append({
                        "name": "invalid_email_count_zero",
                        "description": "Verifier with email_count = 0 (should fail)",
                        "method": method,
                        "endpoint": endpoint_path,
                        "body": invalid_email_count_zero_body,
                        "expected_status": [400, 422],
                    })
        
        # Verifier single endpoint error tests
        if endpoint_path == "/api/v3/email/verifier/single/" and method == "POST":
            if valid_body:
                # Missing required fields
                test_cases.append({
                    "name": "missing_required_fields",
                    "description": "Verifier single without required fields (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": {},
                    "expected_status": [400, 422],
                })
                
                # Missing first_name
                missing_first_name_body = valid_body.copy()
                missing_first_name_body.pop("first_name", None)
                test_cases.append({
                    "name": "missing_first_name",
                    "description": "Verifier single without first_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_first_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing last_name
                missing_last_name_body = valid_body.copy()
                missing_last_name_body.pop("last_name", None)
                test_cases.append({
                    "name": "missing_last_name",
                    "description": "Verifier single without last_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_last_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing domain
                missing_domain_body = valid_body.copy()
                missing_domain_body.pop("domain", None)
                test_cases.append({
                    "name": "missing_domain",
                    "description": "Verifier single without domain (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_domain_body,
                    "expected_status": [400, 422],
                })
        
        return test_cases
