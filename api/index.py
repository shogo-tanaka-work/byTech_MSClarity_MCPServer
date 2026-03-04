"""
Vercel API Routes for Microsoft Clarity MCP Server
Simple HTTP handler for Vercel Python runtime
"""

import json
import os
import asyncio
from http.server import BaseHTTPRequestHandler

# Import Clarity API Client
try:
    from clarity_mcp_server.api_client import ClarityAPIClient
except ImportError:
    # For Vercel deployment, try relative import
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from clarity_mcp_server.api_client import ClarityAPIClient


class handler(BaseHTTPRequestHandler):
    """
    HTTP request handler for Vercel
    """

    def do_GET(self):
        """Handle GET requests"""
        try:
            path = self.path

            if path == '/':
                self._send_json_response(200, {
                    'name': '@microsoft/clarity-mcp-server',
                    'version': '1.0.0',
                    'description': 'Microsoft Clarity Data Export MCP Server'
                })

            elif path == '/health':
                self._send_json_response(200, {'status': 'healthy'})

            elif path == '/info':
                self._send_json_response(200, {
                    'server': {
                        'name': '@microsoft/clarity-mcp-server',
                        'version': '1.0.0'
                    },
                    'capabilities': {
                        'tools': {
                            'get-clarity-data': {
                                'description': 'Fetch Microsoft Clarity analytics data',
                                'parameters': {
                                    'numOfDays': {
                                        'type': 'integer',
                                        'description': 'Number of days to retrieve (1-3)',
                                        'minimum': 1,
                                        'maximum': 3
                                    },
                                    'dimensions': {
                                        'type': 'array',
                                        'items': {'type': 'string'},
                                        'description': 'Array of dimensions to filter by (max 3)',
                                        'maxItems': 3
                                    },
                                    'metrics': {
                                        'type': 'array',
                                        'items': {'type': 'string'},
                                        'description': 'Array of metrics to retrieve'
                                    },
                                    'token': {
                                        'type': 'string',
                                        'description': 'Clarity API token (optional if set via environment)'
                                    },
                                    'context': {
                                        'type': 'string',
                                        'description': 'Additional context for the query',
                                        'maxLength': 1024
                                    }
                                }
                            }
                        }
                    },
                    'api_info': {
                        'available_metrics': ["ScrollDepth", "EngagementTime", "Traffic", "PopularPages", "Browser", "Device", "OS", "Country/Region", "PageTitle", "ReferrerURL", "DeadClickCount", "ExcessiveScroll", "RageClickCount", "QuickbackClick", "ScriptErrorCount", "ErrorClickCount"],
                        'available_dimensions': ["Browser", "Device", "Country/Region", "OS", "Source", "Medium", "Campaign", "Channel", "URL"],
                        'api_base_url': "https://www.clarity.ms/export-data/api/v1/project-live-insights"
                    }
                })

            else:
                self._send_json_response(404, {'error': 'Not found'})

        except Exception as e:
            self._send_json_response(500, {'error': str(e)})

    def do_POST(self):
        """Handle POST requests"""
        try:
            path = self.path
            content_length = int(self.headers.get('Content-Length', 0))

            # Read request body
            body = {}
            if content_length > 0:
                body_data = self.rfile.read(content_length)
                try:
                    body = json.loads(body_data.decode('utf-8'))
                except:
                    body = {}

            if path == '/api/clarity-data':
                self._handle_clarity_data(body)
            elif path == '/mcp':
                self._handle_mcp(body)
            else:
                self._send_json_response(404, {'error': 'Not found'})

        except Exception as e:
            self._send_json_response(500, {'error': str(e)})

    def _handle_clarity_data(self, body):
        """Handle clarity data requests"""
        # Validate required parameters
        num_of_days = body.get('numOfDays')
        if not num_of_days:
            self._send_json_response(400, {'error': 'numOfDays is required'})
            return

        if not isinstance(num_of_days, int) or num_of_days < 1 or num_of_days > 3:
            self._send_json_response(400, {'error': 'numOfDays must be an integer between 1 and 3'})
            return

        # Get optional parameters
        dimensions = body.get('dimensions', [])
        metrics = body.get('metrics', [])
        context = body.get('context')
        token = body.get('token')

        # Validate dimensions (max 3)
        if len(dimensions) > 3:
            self._send_json_response(400, {'error': 'Maximum 3 dimensions allowed'})
            return

        # Run async API call
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self._fetch_clarity_data_async(
                num_of_days, dimensions, metrics, context, token
            ))
            self._send_json_response(200, result)
        except Exception as e:
            self._send_json_response(500, {'error': f'Internal server error: {str(e)}'})
        finally:
            loop.close()

    async def _fetch_clarity_data_async(self, num_of_days, dimensions=None, metrics=None, context=None, token=None):
        """Fetch Clarity data asynchronously"""
        try:
            # Initialize API client
            client = ClarityAPIClient(api_token=token)

            # Validate dimensions
            if dimensions:
                dimensions = client.validate_dimensions(dimensions)

            # Fetch data from API
            api_response = await client.fetch_clarity_data(
                num_of_days=num_of_days,
                dimensions=dimensions,
                context=context,
                api_token=token
            )

            # Check for API errors
            if isinstance(api_response, dict) and 'error' in api_response:
                return {'error': api_response['error']}

            # Process the response data based on structure
            if isinstance(api_response, dict):
                data = api_response.get('data', [])
            elif isinstance(api_response, list):
                data = api_response
            else:
                return {'error': f'Unexpected API response type: {type(api_response)}'}

            # Filter by metrics if specified
            if metrics and isinstance(data, list):
                data = client.filter_metrics(data, metrics)

            # Return formatted response
            return {
                'data': data,
                'total_records': len(data) if isinstance(data, list) else 0,
                'parameters': {
                    'numOfDays': num_of_days,
                    'dimensions': dimensions or [],
                    'metrics': metrics or [],
                    'context': context
                },
                'api_info': {
                    'available_metrics': client.AVAILABLE_METRICS,
                    'available_dimensions': client.AVAILABLE_DIMENSIONS,
                    'api_base_url': client.API_BASE_URL
                }
            }

        except Exception as e:
            return {'error': f'Failed to fetch Clarity data: {str(e)}'}

    def _handle_mcp(self, body):
        """Handle MCP requests (JSON-RPC 2.0)"""
        method = body.get('method')
        request_id = body.get('id')
        params = body.get('params', {})

        if method == 'initialize':
            self._send_json_response(200, {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': {
                    'protocolVersion': '2024-11-05',
                    'capabilities': {'tools': {'listChanged': False}},
                    'serverInfo': {'name': 'Clarity MCP Server', 'version': '1.0.0'}
                }
            })

        elif method == 'tools/list':
            self._send_json_response(200, {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': {
                    'tools': [{
                        'name': 'get-clarity-data',
                        'description': 'Fetch Microsoft Clarity analytics data',
                        'inputSchema': {
                            'type': 'object',
                            'properties': {
                                'numOfDays': {
                                    'type': 'integer',
                                    'description': 'Number of days to retrieve (1-3)',
                                    'minimum': 1,
                                    'maximum': 3
                                },
                                'dimensions': {
                                    'type': 'array',
                                    'items': {'type': 'string'},
                                    'description': 'Array of dimensions to filter by (max 3)',
                                    'maxItems': 3
                                },
                                'metrics': {
                                    'type': 'array',
                                    'items': {'type': 'string'},
                                    'description': 'Array of metrics to retrieve'
                                },
                                'token': {
                                    'type': 'string',
                                    'description': 'Clarity API token (optional if set via environment)'
                                },
                                'context': {
                                    'type': 'string',
                                    'description': 'Additional context for the query',
                                    'maxLength': 1024
                                }
                            },
                            'required': ['numOfDays']
                        }
                    }]
                }
            })

        elif method == 'tools/call':
            tool_name = params.get('name')
            arguments = params.get('arguments', {})

            if tool_name == 'get-clarity-data':
                num_of_days = arguments.get('numOfDays', 1)
                dimensions = arguments.get('dimensions', [])
                metrics = arguments.get('metrics', [])
                context = arguments.get('context')
                token = arguments.get('token')

                if not isinstance(num_of_days, int) or num_of_days < 1 or num_of_days > 3:
                    num_of_days = 1
                if len(dimensions) > 3:
                    dimensions = dimensions[:3]

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(self._fetch_clarity_data_async(
                        num_of_days, dimensions, metrics, context, token
                    ))
                    self._send_json_response(200, {
                        'jsonrpc': '2.0',
                        'id': request_id,
                        'result': {'content': [{'type': 'text', 'text': json.dumps(result)}]}
                    })
                except Exception as e:
                    self._send_json_response(200, {
                        'jsonrpc': '2.0',
                        'id': request_id,
                        'error': {'code': -32603, 'message': f'Tool execution failed: {str(e)}'}
                    })
                finally:
                    loop.close()
            else:
                self._send_json_response(200, {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'error': {'code': -32601, 'message': f'Unknown tool: {tool_name}'}
                })

        else:
            self._send_json_response(200, {
                'jsonrpc': '2.0',
                'id': request_id,
                'error': {'code': -32601, 'message': f"Method '{method}' not found"}
            })

    def _send_json_response(self, status_code, data):
        """Send JSON response"""
        response_body = json.dumps(data).encode('utf-8')

        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)