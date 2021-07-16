#!/bin/bash
curl -u elastic:bigsec.com localhost:9200/_template/tourbillon -H 'Content-Type: application/json' -d '{
	"index_patterns": ["tourbillon_*"],
	"settings": {
		"index.number_of_shards": 5,
		"number_of_replicas": 0
	},
	"mappings": {
		"doc": {
            "dynamic": true,
			"properties": {
				"@timestamp": {
					"type": "date",
					"index": "true"
				},
				"log_time": {
					"type": "date",
					"index": "true"
				},
				"host": {
					"type": "text",
					"index": "true"
				},
				"log_app": {
					"type": "text",
					"index": "true"
				},
				"log_level": {
					"type": "text",
					"index": "true"
				},
				"log_msg": {
					"type": "keyword",
					"index": "true"
				},
                "log_sub_level": {
					"type": "text",
					"index": "true"
				},
                "request_id": {
					"type": "keyword",
					"index": "true"
				},
                "order_id": {
					"type": "text",
					"index": "true"
				},
                "frame_id_chain": {
					"type": "text",
					"index": "true"
				},
                "frame_name": {
					"type": "text",
					"index": "true"
				},
                "ota_name": {
					"type": "text",
					"index": "true"
				},
                "provider_channel": {
					"type": "text",
					"index": "true"
				},

				"message": {
					"type": "text"
				},
				"path": {
					"type": "text"
				},
				"private_ip": {
					"type": "text",
					"index": "true"
				},
				"public_ip": {
					"type": "text",
					"index": "true"
				},
				"tags": {
					"type": "keyword",
					"index": "true"
				},
				"latency": {
					"type": "long",
					"index": "true"
				},
				"exception": {
					"type": "keyword",
					"index": "true"
				},
				"is_req_success": {
					"type": "boolean",
					"index": "true"
				},
				"request_time": {
					"type": "text",
					"index": "true"
				},
				"retries": {
					"type": "long",
					"index": "true"
				},
				"is_req_timeout": {
					"type": "boolean",
					"index": "true"
				},
				"req_raw_data": {
					"type": "text"
				},
				"content": {
					"type": "text"
				},
				"is_proxy_error": {
					"type": "boolean",
					"index": "true"
				},
				"response_status_code": {
					"type": "text",
					"index": "true"
				},
				"req_raw_url": {
					"type": "keyword",
					"index": "true"
				},
                "req_cookie": {
					"type": "text",
					"index": "true"
				},
                "is_redirect": {
					"type": "boolean",
					"index": "true"
				},
                    "response_headers": {
					"type": "text",
					"index": "true"
				},
				"from_date": {
					"type": "keyword",
					"index": "true"
				},
                "ret_date": {
					"type": "keyword",
					"index": "true"
				},
				"from_airport": {
					"type": "keyword",
					"index": "true"
				},
				"to_airport": {
					"type": "keyword",
					"index": "true"
				},
				"return_status": {
					"type": "keyword",
					"index": "true"
				},
				"return_details": {
					"type": "keyword",
					"index": "true"
				},
				"ret": {
					"type": "text",
					"index": "true"
				},
				"req": {
					"type": "text",
					"index": "true"
				},
				"verify_routing_key": {
					"type": "keyword",
					"index": "true"
				},
				"from_city": {
					"type": "keyword",
					"index": "true"
				},
				"to_city": {
					"type": "keyword",
					"index": "true"
				},
				"from_country": {
					"type": "keyword",
					"index": "true"
				},
				"to_country": {
					"type": "keyword",
					"index": "true"
				},
				"adt_count": {
					"type": "long",
					"index": "true"
				},
				"chd_count": {
					"type": "long",
					"index": "true"
				},
				"inf_count": {
					"type": "long",
					"index": "true"
				},
				"total_latency": {
					"type": "long",
					"index": "true"
				},
				"assoc_search_routings_amount": {
					"type": "long",
					"index": "true"
				},
                "fare_operation": {
					"type": "keyword",
					"index": "true"
				},
                "assoc_order_id": {
					"type": "keyword",
					"index": "true"
				},
				"routing_range": {
					"type": "keyword",
					"index": "true"
				},
				"trip_type": {
					"type": "keyword",
					"index": "true"
				}
			}
		}
	}
}'
