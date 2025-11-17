const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2NjQxOThmNy01OWM4LTQwMzktYTEzYy0zZWFlMGIwMTUxMmUiLCJleHAiOjE3NjMzODIyNzYsInR5cGUiOiJhY2Nlc3MifQ.a5BXbaHbkCfPjKyhvF6MHtQSc-0T9HJJlNExJjvkl-A';

// Use the unified /ws endpoint
const ws = new WebSocket(`ws://127.0.0.1:8000/api/v1/contacts/ws?token=${token}`);

// Track pending requests
const pendingRequests = new Set();

ws.onopen = () => {
  console.log('✅ WebSocket Connected');
  console.log('📤 Sending test requests for all 22 WebSocket actions...\n');
  
  let requestCounter = 1;
  
  // Test 1: List Contacts
  setTimeout(() => {
    const requestId = `req-list-${requestCounter++}`;
    pendingRequests.add(requestId);
    console.log(`[1/22] Testing: list_contacts action (request_id: ${requestId})`);
    ws.send(JSON.stringify({
      action: "list_contacts",
      request_id: requestId,
      data: {
        country: "United States",
        limit: 5
      }
    }));
  }, 100);
  
  // Test 2: Get Contact (needs a valid UUID - adjust as needed)
  setTimeout(() => {
    const requestId = `req-get-${requestCounter++}`;
    pendingRequests.add(requestId);
    console.log(`[2/22] Testing: get_contact action (request_id: ${requestId})`);
    ws.send(JSON.stringify({
      action: "get_contact",
      request_id: requestId,
      data: {
        contact_uuid: "REPLACE_WITH_VALID_UUID"
      }
    }));
  }, 500);
  
  // Test 3: Count Contacts
  setTimeout(() => {
    const requestId = `req-count-${requestCounter++}`;
    pendingRequests.add(requestId);
    console.log(`[3/22] Testing: count_contacts action (request_id: ${requestId})`);
    ws.send(JSON.stringify({
      action: "count_contacts",
      request_id: requestId,
      data: {
        country: "United States"
      }
    }));
  }, 900);
  
  // Test 4: Get Contact UUIDs
  setTimeout(() => {
    const requestId = `req-uuids-${requestCounter++}`;
    pendingRequests.add(requestId);
    console.log(`[4/22] Testing: get_contact_uuids action (request_id: ${requestId})`);
    ws.send(JSON.stringify({
      action: "get_contact_uuids",
      request_id: requestId,
      data: {
        country: "United States",
        limit: 10
      }
    }));
  }, 1300);
  
  // // Test 5: Create Contact (admin only - will fail if not admin)
  // setTimeout(() => {
  //   const requestId = `req-create-${requestCounter++}`;
  //   pendingRequests.add(requestId);
  //   console.log(`[5/22] Testing: create_contact action (request_id: ${requestId})`);
  //   ws.send(JSON.stringify({
  //     action: "create_contact",
  //     request_id: requestId,
  //     data: {
  //       write_key: "YOUR_WRITE_KEY_HERE",
  //       first_name: "Test",
  //       last_name: "User",
  //       email: "test@example.com"
  //     }
  //   }));
  // }, 1700);
  
  // Test 6: Get Titles
  setTimeout(() => {
    const requestId = `req-titles-${requestCounter++}`;
    pendingRequests.add(requestId);
    console.log(`[6/22] Testing: get_titles action (request_id: ${requestId})`);
    ws.send(JSON.stringify({
      action: "get_titles",
      request_id: requestId,
      data: {
        search: "CEO",
        distinct: true,
        limit: 10
      }
    }));
  }, 2100);
  
  // Test 7: Get Companies
  setTimeout(() => {
    const requestId = `req-companies-${requestCounter++}`;
    pendingRequests.add(requestId);
    console.log(`[7/22] Testing: get_companies action (request_id: ${requestId})`);
    ws.send(JSON.stringify({
      action: "get_companies",
      request_id: requestId,
      data: {
        search: "Tech",
        distinct: true,
        limit: 10
      }
    }));
  }, 2500);
  
  // Test 8: Get Industries
  setTimeout(() => {
    const requestId = `req-industries-${requestCounter++}`;
    pendingRequests.add(requestId);
    console.log(`[8/22] Testing: get_industries action (request_id: ${requestId})`);
    ws.send(JSON.stringify({
      action: "get_industries",
      request_id: requestId,
      data: {
        distinct: true,
        separated: false,
        limit: 10
      }
    }));
  }, 2900);
  
  // Test 9: Get Keywords
  setTimeout(() => {
    const requestId = `req-keywords-${requestCounter++}`;
    pendingRequests.add(requestId);
    console.log(`[9/22] Testing: get_keywords action (request_id: ${requestId})`);
    ws.send(JSON.stringify({
      action: "get_keywords",
      request_id: requestId,
      data: {
        search: "cloud",
        distinct: true,
        separated: true,
        limit: 10
      }
    }));
  }, 3300);
  
  // Test 10: Get Technologies
  setTimeout(() => {
    const requestId = `req-technologies-${requestCounter++}`;
    pendingRequests.add(requestId);
    console.log(`[10/22] Testing: get_technologies action (request_id: ${requestId})`);
    ws.send(JSON.stringify({
      action: "get_technologies",
      request_id: requestId,
      data: {
        search: "python",
        distinct: true,
        separated: true,
        limit: 10
      }
    }));
  }, 3700);
  
  // Test 11: Get Company Addresses
  setTimeout(() => {
    const requestId = `req-company-addr-${requestCounter++}`;
    pendingRequests.add(requestId);
    console.log(`[11/22] Testing: get_company_addresses action (request_id: ${requestId})`);
    ws.send(JSON.stringify({
      action: "get_company_addresses",
      request_id: requestId,
      data: {
        search: "San Francisco",
        distinct: true,
        limit: 10
      }
    }));
  }, 4100);
  
  // Test 12: Get Contact Addresses
  setTimeout(() => {
    const requestId = `req-contact-addr-${requestCounter++}`;
    pendingRequests.add(requestId);
    console.log(`[12/22] Testing: get_contact_addresses action (request_id: ${requestId})`);
    ws.send(JSON.stringify({
      action: "get_contact_addresses",
      request_id: requestId,
      data: {
        search: "Austin",
        distinct: true,
        limit: 10
      }
    }));
  }, 4500);
  
  // Test 13: Get Cities
  setTimeout(() => {
    const requestId = `req-cities-${requestCounter++}`;
    pendingRequests.add(requestId);
    console.log(`[13/22] Testing: get_cities action (request_id: ${requestId})`);
    ws.send(JSON.stringify({
      action: "get_cities",
      request_id: requestId,
      data: {
        search: "San",
        distinct: true,
        limit: 10
      }
    }));
  }, 4900);
  
  // Test 14: Get States
  setTimeout(() => {
    const requestId = `req-states-${requestCounter++}`;
    pendingRequests.add(requestId);
    console.log(`[14/22] Testing: get_states action (request_id: ${requestId})`);
    ws.send(JSON.stringify({
      action: "get_states",
      request_id: requestId,
      data: {
        distinct: true,
        limit: 10
      }
    }));
  }, 5300);
  
  // Test 15: Get Countries
  setTimeout(() => {
    const requestId = `req-countries-${requestCounter++}`;
    pendingRequests.add(requestId);
    console.log(`[15/22] Testing: get_countries action (request_id: ${requestId})`);
    ws.send(JSON.stringify({
      action: "get_countries",
      request_id: requestId,
      data: {
        distinct: true,
        limit: 10
      }
    }));
  }, 5700);
  
  // Test 16: Get Company Cities
  setTimeout(() => {
    const requestId = `req-company-cities-${requestCounter++}`;
    pendingRequests.add(requestId);
    console.log(`[16/22] Testing: get_company_cities action (request_id: ${requestId})`);
    ws.send(JSON.stringify({
      action: "get_company_cities",
      request_id: requestId,
      data: {
        distinct: true,
        limit: 10
      }
    }));
  }, 6100);
  
  // Test 17: Get Company States
  setTimeout(() => {
    const requestId = `req-company-states-${requestCounter++}`;
    pendingRequests.add(requestId);
    console.log(`[17/22] Testing: get_company_states action (request_id: ${requestId})`);
    ws.send(JSON.stringify({
      action: "get_company_states",
      request_id: requestId,
      data: {
        distinct: true,
        limit: 10
      }
    }));
  }, 6500);
  
  // Test 18: Get Company Countries
  setTimeout(() => {
    const requestId = `req-company-countries-${requestCounter++}`;
    pendingRequests.add(requestId);
    console.log(`[18/22] Testing: get_company_countries action (request_id: ${requestId})`);
    ws.send(JSON.stringify({
      action: "get_company_countries",
      request_id: requestId,
      data: {
        distinct: true,
        limit: 10
      }
    }));
  }, 6900);
  
  // Test 19: Get Import Info
  setTimeout(() => {
    const requestId = `req-import-info-${requestCounter++}`;
    pendingRequests.add(requestId);
    console.log(`[19/22] Testing: get_import_info action (request_id: ${requestId})`);
    ws.send(JSON.stringify({
      action: "get_import_info",
      request_id: requestId,
      data: {}
    }));
  }, 7300);
  
  // Test 20: Upload Contacts CSV (admin only - will fail if not admin)
  setTimeout(() => {
    const requestId = `req-upload-${requestCounter++}`;
    pendingRequests.add(requestId);
    console.log(`[20/22] Testing: upload_contacts_csv action (request_id: ${requestId})`);
    // Note: This requires a base64-encoded CSV file
    // For testing, you would need to provide actual file data
    ws.send(JSON.stringify({
      action: "upload_contacts_csv",
      request_id: requestId,
      data: {
        file_name: "test_contacts.csv",
        file_data: "base64_encoded_csv_content_here"
      }
    }));
  }, 7700);
  
  // Test 21: Get Import Status (needs a valid job_id)
  setTimeout(() => {
    const requestId = `req-import-status-${requestCounter++}`;
    pendingRequests.add(requestId);
    console.log(`[21/22] Testing: get_import_status action (request_id: ${requestId})`);
    ws.send(JSON.stringify({
      action: "get_import_status",
      request_id: requestId,
      data: {
        job_id: "REPLACE_WITH_VALID_JOB_ID",
        include_errors: false
      }
    }));
  }, 8100);
  
  // Test 22: Get Import Errors (needs a valid job_id)
  setTimeout(() => {
    const requestId = `req-import-errors-${requestCounter++}`;
    pendingRequests.add(requestId);
    console.log(`[22/22] Testing: get_import_errors action (request_id: ${requestId})`);
    ws.send(JSON.stringify({
      action: "get_import_errors",
      request_id: requestId,
      data: {
        job_id: "REPLACE_WITH_VALID_JOB_ID"
      }
    }));
  }, 8500);
};

ws.onmessage = (event) => {
  const response = JSON.parse(event.data);
  const { request_id, action, status, data, error } = response;
  
  // Remove from pending
  pendingRequests.delete(request_id);
  
  console.log(`\n📥 Response received for ${action} (request_id: ${request_id})`);
  console.log(`   Status: ${status}`);
  
  if (status === "success") {
    console.log(`   ✅ Success!`);
    
    // Display relevant data based on action
    if (action === "list_contacts") {
      console.log(`   👥 Contacts found: ${data.results?.length || 0}`);
      if (data.results && data.results.length > 0) {
        console.log(`   🔍 First contact:`, data.results[0].first_name || data.results[0].email || 'N/A');
      }
    } else if (action === "get_contact") {
      console.log(`   👤 Contact:`, data.first_name || data.email || 'N/A');
    } else if (action === "count_contacts") {
      console.log(`   🔢 Total count: ${data.count || 0} contacts`);
    } else if (action === "get_contact_uuids") {
      console.log(`   🆔 UUIDs returned: ${data.uuids?.length || 0}`);
      console.log(`   📊 Total count: ${data.count || 0}`);
    } else if (action === "create_contact") {
      console.log(`   ✨ Contact created:`, data.uuid || 'N/A');
    } else if (action.startsWith("get_")) {
      console.log(`   📋 Results: ${data.results?.length || 0} items`);
      if (data.results && data.results.length > 0) {
        console.log(`   🔍 First result: ${data.results[0]}`);
      }
    } else if (action === "get_import_info") {
      console.log(`   ℹ️  Info:`, data.message || 'N/A');
    } else if (action === "upload_contacts_csv") {
      console.log(`   📤 Upload job created:`, data.job_id || 'N/A');
      console.log(`   📊 Status:`, data.status || 'N/A');
    } else if (action === "get_import_status") {
      console.log(`   📊 Job status:`, data.status || 'N/A');
      console.log(`   📈 Progress: ${data.processed_rows || 0}/${data.total_rows || 0} rows`);
    } else if (action === "get_import_errors") {
      console.log(`   ❌ Errors found: ${data.errors?.length || 0}`);
    }
  } else {
    console.error(`   ❌ Error:`, error);
  }
  
  // Check if all requests are complete
  if (pendingRequests.size === 0) {
    console.log(`\n✅ All 22 WebSocket actions tested!`);
    console.log(`\n💡 You can close the connection or send more requests.`);
  }
};

ws.onerror = (error) => {
  console.error('❌ WebSocket error:', error);
};

ws.onclose = (event) => {
  console.log(`\n🔌 WebSocket closed:`, {
    code: event.code,
    reason: event.reason || 'No reason provided',
    wasClean: event.wasClean
  });
  
  if (pendingRequests.size > 0) {
    console.warn(`⚠️  Warning: ${pendingRequests.size} requests were still pending when connection closed.`);
  }
};

