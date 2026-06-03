# views.py
import base64
import json
import secrets
import requests
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
from requests_oauthlib.compliance_fixes import facebook

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.shortcuts import redirect
from django.core import signing
from dotenv import load_dotenv
import os
import urllib.request
from urllib.parse import urlparse

from workspace.models import Workspace
from .models import LinkedinToken, LinkedinUser, LinkedinPage
from nano_banana.models import NanoBananaImage
from utils.public_urls import public_media_url
from rest_framework_simplejwt.tokens import RefreshToken
load_dotenv()


LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
DEFAULT_BACKEND_URL = (
    os.getenv("PUBLIC_BACKEND_URL")
    or os.getenv("BACKEND_URL")
    or "https://api.voicespark.ai"
).rstrip("/")
LINKEDIN_REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI") or f"{DEFAULT_BACKEND_URL}/auth/linkedin/callback/"

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
LINKEDIN_ORG_ACLS_URL = "https://api.linkedin.com/rest/organizationAcls"
LINKEDIN_ORG_DETAILS_URL = "https://api.linkedin.com/rest/organizations"

class LinkedinLogin(APIView):
    def get(self, request, *args, **kwargs):
        user_id = request.query_params.get("user_id", "1")
        workspace_id =  request.query_params.get("workspace_id", "1")
        if not user_id:
            return Response(
                {"error": "user_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        state = signing.dumps({
            "user_id": str(user_id),
            "workspace_id": str(workspace_id),
            "nonce": secrets.token_urlsafe(24),
        }, salt="linkedin-oauth-state")

        params = {
            "response_type": "code",
            "client_id": LINKEDIN_CLIENT_ID,
            "redirect_uri": LINKEDIN_REDIRECT_URI,
            "scope": "openid profile email w_member_social w_organization_social r_organization_social rw_organization_admin",
            "state": state,
        }
        # auth_url = requests.Request("GET", LINKEDIN_AUTH_URL, params=params).prepare().url
        auth_url = f"{LINKEDIN_AUTH_URL}?{urlencode(params)}"
        # return Response({"auth_url": auth_url, "state": state}, status=status.HTTP_200_OK)
        return redirect(str(auth_url))

class LinkedinAuthCallback(APIView):
    def get(self, request, *args, **kwargs):
        def popup_response(message, success=False, status_code=200):
            event = "linkedin_login_success" if success else "linkedin_login_failure"
            safe_message = json.dumps(str(message))
            response = HttpResponse(f"""
                <html>
                    <body>
                        <script>
                            (function () {{
                                try {{
                                    if (window.opener && !window.opener.closed) {{
                                        window.opener.postMessage({json.dumps(event)}, "*");
                                    }}
                                }} catch (error) {{}}
                                window.close();
                                setTimeout(function () {{
                                    window.close();
                                    document.body.innerHTML = {safe_message} + "<br/>This window can be closed.";
                                }}, 300);
                            }})();
                        </script>
                        <noscript>{str(message)}</noscript>
                    </body>
                </html>
            """, status=status_code)
            response["Cross-Origin-Opener-Policy"] = "unsafe-none"
            return response

        code = request.GET.get('code')
        state = request.GET.get('state')

        if not code or not state:
            return popup_response(
                "Both 'code' and 'state' are required.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Separate user_id and random token from state
        try:
            state_data = signing.loads(state, salt="linkedin-oauth-state", max_age=600)
            user_id = state_data.get("user_id")
            workspace_id = state_data.get("workspace_id")
        except signing.SignatureExpired:
            return popup_response("LinkedIn login expired. Please try again.", status_code=status.HTTP_400_BAD_REQUEST)
        except signing.BadSignature:
            return popup_response("Invalid LinkedIn login state. Please try again.", status_code=status.HTTP_400_BAD_REQUEST)

        if not user_id:
            return popup_response("Invalid LinkedIn login state. Please try again.", status_code=status.HTTP_400_BAD_REQUEST)

        # Step 2: Exchange code for access token
        token_response = requests.post(
            LINKEDIN_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": LINKEDIN_REDIRECT_URI,
                "client_id": LINKEDIN_CLIENT_ID,
                "client_secret": LINKEDIN_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if token_response.status_code != 200:
            return popup_response(
                f"Failed to obtain access token: {token_response.text}",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        token_data = token_response.json()
        access_token = token_data.get("access_token")
        # print('token_data',token_data)
        # Step 3: Fetch user info
        userinfo_response = requests.get(
            LINKEDIN_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if userinfo_response.status_code != 200:
            return popup_response(
                f"Failed to fetch user info: {userinfo_response.text}",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        userinfo = userinfo_response.json()
        # print('userinfo', userinfo)
        # email = userinfo.get("email")
        # first_name = userinfo.get("given_name", "")
        # last_name = userinfo.get("family_name", "")

        # if not email:
        #     return Response(
        #         {"error": "Email not available from LinkedIn."},
        #         status=status.HTTP_400_BAD_REQUEST,
        #     )

        # Step 4: Get or create user
        user, created = User.objects.get_or_create(
            id=int(user_id),
        )
        workspace = Workspace.objects.filter(id=workspace_id).first()
        LinkedinToken.objects.update_or_create(
            user=user,
            defaults={
                "access_token": access_token,
                "token_type": token_data.get("token_type", "bearer"),
                "expires_in": token_data.get("expires_in"),
                "id_token": token_data.get("id_token"),
                "workspace":workspace
            },
        )
        LinkedinUser.objects.update_or_create(
            user=user,
            defaults={
                "email": userinfo.get("email", ""),
                "first_name": userinfo.get("given_name"),
                "last_name": userinfo.get("family_name"),
                "full_name": userinfo.get("name"),
                "picture_url": userinfo.get("picture", ""),
                "workspace":workspace
            },
        )

        # Fetch managed LinkedIn pages
        fetch_linkedin_pages(access_token, user, workspace)

        return popup_response("LinkedIn connected.", success=True)

def fetch_linkedin_pages(access_token, user, workspace):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202604",
    }
    
    params = {
        "q": "roleAssignee",
        "state": "APPROVED",
    }
    # We'll fetch all roles and filter in code or request multiple if supported
    roles = ["ADMINISTRATOR", "DIRECT_SPONSORED_CONTENT_POSTER", "CONTENT_ADMIN"]
    
    try:
        # Note: LinkedIn Rest API versioning is strict. 
        # The URL might need to be structured correctly for the Posts API context.
        # But for /organizationAcls, version 202604 is what the user requested for headers.
        
        # We need to loop roles if the API doesn't support list (LinkedIn usually doesn't for role query)
        for role in roles:
            current_params = params.copy()
            current_params["role"] = role
            
            response = requests.get(LINKEDIN_ORG_ACLS_URL, headers=headers, params=current_params)
            if response.status_code != 200:
                continue
                
            acls = response.json().get("elements", [])
            for acl in acls:
                org_urn = acl.get("organization")
                if not org_urn:
                    continue
                
                org_id = org_urn.split(":")[-1]
                
                # Fetch organization details
                details_url = f"{LINKEDIN_ORG_DETAILS_URL}/{org_id}"
                details_resp = requests.get(details_url, headers=headers)
                if details_resp.status_code == 200:
                    details = details_resp.json()
                    name = details.get("localizedName", "Unknown Organization")
                    vanity_name = details.get("vanityName", "")
                    
                    LinkedinPage.objects.update_or_create(
                        workspace=workspace,
                        organization_id=org_id,
                        defaults={
                            "user": user,
                            "organization_urn": org_urn,
                            "name": name,
                            "vanity_name": vanity_name,
                            "role": role,
                        }
                    )
        return True
    except Exception as e:
        print(f"Error fetching LinkedIn pages: {e}")
        return False

class ConnectedPagesView(APIView):
    def get(self, request):
        user_id = request.query_params.get("user_id")
        workspace_id = request.query_params.get("workspace_id")
        
        pages = LinkedinPage.objects.filter(workspace_id=workspace_id)
        data = []
        for page in pages:
            data.append({
                "id": page.id,
                "organization_id": page.organization_id,
                "organization_urn": page.organization_urn,
                "name": page.name,
                "vanity_name": page.vanity_name,
                "logo_url": page.logo_url,
                "role": page.role,
                "is_selected": page.is_selected
            })
        return Response({"pages": data}, status=status.HTTP_200_OK)

class SelectLinkedinPageView(APIView):
    def post(self, request):
        page_id = request.data.get("page_id")
        workspace_id = request.data.get("workspace_id")
        
        # Deselect others in the same workspace
        LinkedinPage.objects.filter(workspace_id=workspace_id).update(is_selected=False)
        
        # Select the chosen one
        try:
            page = LinkedinPage.objects.get(id=page_id, workspace_id=workspace_id)
            page.is_selected = True
            page.save()
            return Response({"success": True, "message": f"Page '{page.name}' selected."}, status=status.HTTP_200_OK)
        except LinkedinPage.DoesNotExist:
            return Response({"error": "Page not found in this workspace."}, status=status.HTTP_404_NOT_FOUND)

LINKEDIN_POST_URL = "https://api.linkedin.com/rest/posts"
LINKEDIN_ASSETS_URL = "https://api.linkedin.com/rest/images?action=initializeUpload"


class LinkedinCreatePost(APIView):
    def post(self, request, *args, **kwargs):
        user_id = request.data.get('user_id', '2')
        nano_banana_id = request.data.get('nano_banana_id', "")
        user = User.objects.filter(id=int(user_id)).first()
        if not nano_banana_id:
            return JsonResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR, data={
                'error': "Did not receive nano banana id"
            })
        nano_banana = NanoBananaImage.objects.filter(id=nano_banana_id).first()

        # Get stored access token
        try:
            linkedin_token = LinkedinToken.objects.get(user=user, workspace=nano_banana.workspace)
        except LinkedinToken.DoesNotExist:
            return Response(
                {"error": "LinkedIn account not connected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Load the selected LinkedIn page for this workspace
        page = LinkedinPage.objects.filter(workspace=nano_banana.workspace, is_selected=True).first()
        if not page:
            return Response(
                {"error": "Please select a LinkedIn Company Page before publishing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        access_token = linkedin_token.access_token
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202604",
        }

        author_urn = page.organization_urn
        caption = (nano_banana.platform_captions or {}).get('linkedin') or nano_banana.caption

        # Handle Image Upload if needed
        asset_urn = None
        if nano_banana.picture_url:
            # Step A: Initialize upload
            init_payload = {
                "initializeUploadRequest": {
                    "owner": author_urn
                }
            }
            init_resp = requests.post(LINKEDIN_ASSETS_URL, json=init_payload, headers=headers)
            if init_resp.status_code != 200:
                return Response({"error": "Failed to initialize image upload.", "details": init_resp.json()}, status=400)
            
            init_data = init_resp.json()["value"]
            upload_url = init_data["uploadUrl"]
            asset_urn = init_data["image"]

            # Step B: Upload image binary
            try:
                img_resp = requests.get(public_media_url(nano_banana.picture_url), timeout=30)
                img_resp.raise_for_status()
                
                put_headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": img_resp.headers.get("Content-Type", "image/jpeg")
                }
                upload_resp = requests.put(upload_url, data=img_resp.content, headers=put_headers)
                upload_resp.raise_for_status()
            except Exception as e:
                return Response({"error": f"Failed to upload image binary: {str(e)}"}, status=400)

        # Create the Post with new Posts API
        payload = {
            "author": author_urn,
            "commentary": caption,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": []
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False
        }

        if asset_urn:
            payload["content"] = {
                "media": {
                    "title": "VoiceSpark Post",
                    "id": asset_urn
                }
            }

        post_response = requests.post(
            LINKEDIN_POST_URL,
            json=payload,
            headers=headers,
        )

        if post_response.status_code not in (201, 200):
            return Response(
                {"error": "Failed to create post.", "details": post_response.json()},
                status=status.HTTP_400_BAD_REQUEST,
            )

        post_urn = post_response.headers.get("x-restli-id")
        return Response(
            {
                "success": True,
                "message": "Post created successfully.",
                "external_post_id": post_urn,
                "post_urn": post_urn,
                "x-restli-id": post_urn,
                "post_url": f"https://www.linkedin.com/feed/update/{post_urn}",
                "posted_as": "organization",
                "organization_id": page.organization_id,
                "organization_urn": page.organization_urn,
                "organization_name": page.name
            },
            status=status.HTTP_201_CREATED,
        )
