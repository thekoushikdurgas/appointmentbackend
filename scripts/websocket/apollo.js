const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2NjQxOThmNy01OWM4LTQwMzktYTEzYy0zZWFlMGIwMTUxMmUiLCJleHAiOjE3NjMzODI2MjIsInR5cGUiOiJhY2Nlc3MifQ.UpcpqQejUUOaz0KptcQmUQoBGKTa6VMr34PGbW-S2kA';
// const token = 'YOUR_ACCESS_TOKEN_HERE';

// Test URL - can be modified for different test scenarios
const testUrl = "https://app.apollo.io/#/people?page=1&contactEmailStatusV2[]=verified&contactEmailExcludeCatchAll=true&personTitles[]=Travel%20Manager&personTitles[]=Global%20Travel%20Manager&personTitles[]=Corporate%20Travel%20Manager&personTitles[]=Senior%20Travel%20Manager&personTitles[]=Travel%20Program%20Manager&personTitles[]=Global%20Travel%20Program%20Manager&personTitles[]=Travel%20Operations%20Manager&personTitles[]=Travel%20Services%20Manager&personTitles[]=Travel%20%26%20Expense%20Manager&personTitles[]=T%26E%20Manager&personTitles[]=Travel%20Procurement%20Manager&personTitles[]=Head%20of%20Travel&personTitles[]=Head%20of%20Corporate%20Travel&personTitles[]=Director%20of%20Travel&personTitles[]=Director%20of%20Global%20Travel&personTitles[]=Director%20of%20Travel%20%26%20Expense&personTitles[]=Director%20of%20Travel%20Operations&personTitles[]=Travel%20Procurement%20Director&personTitles[]=Travel%20Category%20Manager&personTitles[]=Senior%20Category%20Manager%20%E2%80%93%20Travel&personTitles[]=Global%20Category%20Manager%20%E2%80%93%20Travel&personTitles[]=Sourcing%20Manager%20%E2%80%93%20Travel&personTitles[]=Strategic%20Sourcing%20Manager%20%28Travel%29&personTitles[]=Finance%20Operations%20Manager&personTitles[]=Expense%20Management%20Manager&personTitles[]=Shared%20Services%20Manager%20%28T%26E%29&personTitles[]=Accounts%20Payable%20Manager&personTitles[]=Controller%20%28T%26E%29&personTitles[]=Expense%20Compliance%20Manager&personTitles[]=Mobility%20Manager&personTitles[]=Global%20Mobility%20Manager&personTitles[]=Employee%20Mobility%20Lead&personTitles[]=Office%20%26%20Travel%20Manager&personTitles[]=VP%20of%20Procurement&personTitles[]=VP%20of%20Operations&personTitles[]=VP%20Finance&personTitles[]=Chief%20Procurement%20Officer&personTitles[]=Chief%20Operating%20Officer&personTitles[]=Travel&personTitles[]=Expense&personTitles[]=Procurement%20Manager&personTitles[]=Senior%20Procurement%20Manager&personTitles[]=Global%20Procurement%20Manager&personTitles[]=Strategic%20Procurement%20Manager&personTitles[]=Procurement%20Operations%20Manager&personTitles[]=Procurement%20Lead&personTitles[]=Procurement%20Specialist&personTitles[]=Procurement%20Analyst&personTitles[]=Purchasing%20Manager&personTitles[]=Senior%20Purchasing%20Manager&personTitles[]=Category%20Manager&personTitles[]=Senior%20Category%20Manager&personTitles[]=Global%20Category%20Manager&personTitles[]=Sourcing%20Manager&personTitles[]=Senior%20Sourcing%20Manager&personTitles[]=Strategic%20Sourcing%20Manager&personTitles[]=Global%20Sourcing%20Manager&personTitles[]=Indirect%20Procurement%20Manager&personTitles[]=Indirect%20Sourcing%20Manager&personTitles[]=Direct%20Procurement%20Manager&personTitles[]=Direct%20Sourcing%20Manager&personTitles[]=Procurement%20%26%20Supply%20Chain%20Manager&personTitles[]=Supplier%20Management%20Manager&personTitles[]=Vendor%20Manager&personTitles[]=Vendor%20Relations%20Manager&personTitles[]=Head%20of%20Procurement&personTitles[]=Head%20of%20Purchasing&personTitles[]=Director%20of%20Procurement&personTitles[]=Director%20of%20Strategic%20Sourcing&personTitles[]=Director%20of%20Purchasing&personTitles[]=T%26E&personSeniorities[]=manager&personSeniorities[]=director&personSeniorities[]=head&personSeniorities[]=vp&personSeniorities[]=partner&personSeniorities[]=c_suite&personSeniorities[]=founder&personSeniorities[]=owner&personSeniorities[]=senior&organizationLocations[]=France&organizationLocations[]=Spain&organizationNumEmployeesRanges[]=501%2C1000&organizationNumEmployeesRanges[]=1001%2C2000&organizationNumEmployeesRanges[]=2001%2C5000&organizationNumEmployeesRanges[]=201%2C500&organizationNumEmployeesRanges[]=101%2C200&organizationNumEmployeesRanges[]=5001%2C10000&organizationNumEmployeesRanges[]=10001&sortByField=%5Bnone%5D&sortAscending=false";

// Use the unified /ws endpoint
const ws = new WebSocket(`ws://127.0.0.1:8000/api/v2/apollo/ws?token=${token}`);

// Track pending requests
const pendingRequests = new Set();

ws.onopen = () => {
  console.log('✅ WebSocket Connected');
  console.log('📤 Sending test requests for all 4 WebSocket actions...\n');
  
  // Test 1: Analyze Apollo URL
  setTimeout(() => {
    const requestId = 'req-analyze-1';
    pendingRequests.add(requestId);
    console.log(`[1/4] Testing: analyze action (request_id: ${requestId})`);
    ws.send(JSON.stringify({
      action: "analyze",
      request_id: requestId,
      data: {
        url: testUrl
      }
    }));
  }, 500);
  
  // Test 2: Search Contacts
  setTimeout(() => {
    const requestId = 'req-search-2';
    pendingRequests.add(requestId);
    console.log(`[2/4] Testing: search_contacts action (request_id: ${requestId})`);
    ws.send(JSON.stringify({
      action: "search_contacts",
      request_id: requestId,
      data: {
        url: testUrl,
        limit: 10,
        offset: 0
      }
    }));
  }, 1500);
  
  // Test 3: Count Contacts
  setTimeout(() => {
    const requestId = 'req-count-3';
    pendingRequests.add(requestId);
    console.log(`[3/4] Testing: count_contacts action (request_id: ${requestId})`);
    ws.send(JSON.stringify({
      action: "count_contacts",
      request_id: requestId,
      data: {
        url: testUrl
      }
    }));
  }, 2500);
  
  // Test 4: Get Contact UUIDs
  setTimeout(() => {
    const requestId = 'req-uuids-4';
    pendingRequests.add(requestId);
    console.log(`[4/4] Testing: get_uuids action (request_id: ${requestId})`);
    ws.send(JSON.stringify({
      action: "get_uuids",
      request_id: requestId,
      data: {
        url: testUrl,
        limit: 20
      }
    }));
  }, 3500);
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
    if (action === "analyze") {
      console.log(`   📊 URL Structure:`, data.url_structure);
      console.log(`   📈 Statistics:`, data.statistics);
      console.log(`   📋 Categories: ${data.categories?.length || 0} categories found`);
    } else if (action === "search_contacts") {
      console.log(`   👥 Contacts found: ${data.results?.length || 0}`);
      console.log(`   📄 Total results available: ${data.mapping_summary?.total_apollo_parameters || 'N/A'} parameters mapped`);
      if (data.results && data.results.length > 0) {
        console.log(`   🔍 First contact:`, data.results[0].name || data.results[0].email || 'N/A');
      }
    } else if (action === "count_contacts") {
      console.log(`   🔢 Total count: ${data.count || 0} contacts`);
    } else if (action === "get_uuids") {
      console.log(`   🆔 UUIDs returned: ${data.uuids?.length || 0}`);
      console.log(`   📊 Total count: ${data.count || 0}`);
      if (data.uuids && data.uuids.length > 0) {
        console.log(`   🔍 First UUID: ${data.uuids[0]}`);
      }
    }
  } else {
    console.error(`   ❌ Error:`, error);
  }
  
  // Check if all requests are complete
  if (pendingRequests.size === 0) {
    console.log(`\n✅ All 4 WebSocket actions tested successfully!`);
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