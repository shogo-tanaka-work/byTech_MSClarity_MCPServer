#!/usr/bin/env python3
"""
Test script for Python MCP Server
"""

import subprocess
import json
import time
import requests
import threading
import sys

def test_stdio_mode():
    """Test stdio mode MCP server"""
    print("🧪 Testing stdio mode...")

    # Test initialize request
    init_request = '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}'
    result = subprocess.run(
        ['python3', 'main.py', '--clarity_api_token=dummy_token'],
        input=init_request,
        text=True,
        capture_output=True,
        timeout=10
    )

    # Check if initialize response contains expected fields
    output_lines = result.stdout.strip().split('\n')
    response_line = None
    for line in output_lines:
        if line.startswith('{') and '"protocolVersion"' in line:
            response_line = line
            break

    if response_line:
        response = json.loads(response_line)
        assert response.get('protocolVersion') == '2024-11-05'
        assert 'serverInfo' in response
        assert response['serverInfo']['name'] == '@microsoft/clarity-mcp-server'
        print("✅ Initialize request: PASSED")
    else:
        print("❌ Initialize request: FAILED")
        return False

    # Test tools/list request
    list_request = '{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}'
    result = subprocess.run(
        ['python3', 'main.py', '--clarity_api_token=dummy_token'],
        input=list_request,
        text=True,
        capture_output=True,
        timeout=10
    )

    output_lines = result.stdout.strip().split('\n')
    response_line = None
    for line in output_lines:
        if line.startswith('{') and '"tools"' in line:
            response_line = line
            break

    if response_line:
        response = json.loads(response_line)
        assert 'tools' in response
        assert len(response['tools']) > 0
        tool = response['tools'][0]
        assert tool['name'] == 'get-clarity-data'
        assert 'inputSchema' in tool
        print("✅ Tools/list request: PASSED")
    else:
        print("❌ Tools/list request: FAILED")
        return False

    return True

def test_http_mode():
    """Test HTTP mode server"""
    print("🧪 Testing HTTP mode...")

    # Start HTTP server in background
    server_process = subprocess.Popen([
        'python3', 'main.py', '--http', '--host=127.0.0.1', '--port=8001', '--clarity_api_token=dummy_token'
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Wait for server to start
    time.sleep(2)

    try:
        # Test health endpoint
        response = requests.get('http://127.0.0.1:8001/health', timeout=5)
        assert response.status_code == 200
        assert response.json() == {'status': 'healthy'}
        print("✅ Health endpoint: PASSED")

        # Test info endpoint
        response = requests.get('http://127.0.0.1:8001/info', timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert 'server' in data
        assert data['server']['name'] == '@microsoft/clarity-mcp-server'
        assert 'capabilities' in data
        print("✅ Info endpoint: PASSED")

        # Test clarity data endpoint (should fail with dummy token)
        payload = {'numOfDays': 1, 'dimensions': ['Browser']}
        response = requests.post('http://127.0.0.1:8001/api/clarity-data', json=payload, timeout=5)

        # Check that API call fails with dummy token (either 400 or 500 is acceptable)
        assert response.status_code in [400, 500], f"Unexpected status code: {response.status_code}"
        response_data = response.json()
        assert 'detail' in response_data
        assert 'API request failed' in response_data['detail']
        print("✅ Clarity data endpoint: PASSED (expected failure with dummy token)")

        return True

    finally:
        # Clean up server process
        server_process.terminate()
        server_process.wait(timeout=5)

def main():
    """Run all tests"""
    print("🚀 Testing Python MCP Server Implementation")
    print("=" * 50)

    success = True

    # Test stdio mode
    if not test_stdio_mode():
        success = False

    print()

    # Test HTTP mode
    if not test_http_mode():
        success = False

    print()
    print("=" * 50)
    if success:
        print("🎉 All tests PASSED! Python MCP Server is working correctly.")
        return 0
    else:
        print("❌ Some tests FAILED!")
        return 1

if __name__ == '__main__':
    sys.exit(main())
