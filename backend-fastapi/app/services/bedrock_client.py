import os
import boto3
import json
from typing import Union, Dict, Any

class BedrockClient:
    def __init__(self):
        self.client = None
        
    async def initialize(self):
        if self.client:
            return self.client
            
        self.client = boto3.client(
            'bedrock-runtime',
            region_name=os.getenv('AWS_REGION', 'ap-northeast-1')
        )
        return self.client
        
    async def generate_guarded_response(self, prompt: str) -> str:
        """Claude 3 Haiku を使用した高速回答生成"""
        client = await self.initialize()
        
        # Claude 3 Haikuのメッセージ形式
        body = {
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.1,
            "top_p": 0.9,
            "anthropic_version": "bedrock-2023-05-31"
        }
        
        try:
            print(f"⚡ Calling Claude 3 Haiku...")
            response = client.invoke_model(
                modelId="anthropic.claude-3-haiku-20240307-v1:0",
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            
            # Claude 3 Haikuのレスポンス形式
            if 'content' in response_body and len(response_body['content']) > 0:
                return response_body['content'][0]['text']
            else:
                print(f"⚠️ Unexpected Claude 3 Haiku response format: {response_body}")
                return str(response_body)
            
        except Exception as error:
            print(f"❌ Error generating response with Claude 3 Haiku: {error}")
            print(f"   Attempting fallback to Claude v2:1...")
            
            # フォールバック: Claude v2:1
            try:
                fallback_body = {
                    "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
                    "max_tokens_to_sample": 1000,
                    "temperature": 0.1,
                    "top_p": 0.9,
                }
                
                fallback_response = client.invoke_model(
                    modelId="anthropic.claude-v2:1",
                    body=json.dumps(fallback_body)
                )
                
                fallback_response_body = json.loads(fallback_response['body'].read())
                print(f"✅ Fallback to Claude v2:1 successful")
                return fallback_response_body['completion']
                
            except Exception as fallback_error:
                print(f"❌ Both Claude 3 Haiku and Claude v2:1 failed: {fallback_error}")
                raise fallback_error

# シングルトンインスタンス  
bedrock_client = BedrockClient()
