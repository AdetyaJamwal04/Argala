"""
Example 1: Cyber-Physically Gated Deployment Pipeline.
Demonstrates gating a high-risk production operation behind physical phone approval
using the @requires_approval decorator in a single line of code.
"""

import sys
import time
from argala import ArgalaClient, requires_approval
from argala.client import ArgalaApprovalDeniedError, ArgalaTimeoutError

client = ArgalaClient()


# 1. Non-sensitive step: runs automatically
def build_staging_artifacts():
    print("[Pipeline] Step 1: Compiling and packaging staging artifacts...")
    time.sleep(1)
    print("[Pipeline] Staging build complete.")


# 2. High-risk step: GATED BY PHYSICAL PHONE APPROVAL
@requires_approval(
    action="deploy.production_cluster",
    risk_level="critical",
    prompt="Production deployment requested for release v2.4.0. Authorize rollout?",
    timeout_seconds=60,
    client=client,
)
def deploy_to_production(cluster_name: str, release_tag: str):
    """This code WILL NEVER EXECUTE unless the operator physically taps APPROVE on the phone screen."""
    print(f"\n[PIPELINE EXECUTING] Deploying {release_tag} to {cluster_name}...")
    # Simulate production deployment
    time.sleep(2)
    # Physically announce completion on the phone!
    client.speak("Production deployment completed successfully.")
    client.vibrate(300)
    print("[PIPELINE SUCCESS] Rollout complete.")


def main():
    print("=" * 70)
    print("      ARGALA CI/CD CYBER-PHYSICAL GATING DEMO")
    print("=" * 70)

    # Verify node connection
    try:
        ping = client.ping("pipeline_precheck")
        print(f"[OK] Gateway Connected ({ping.get('gateway_name')}, Latency: {ping.get('_client_latency_ms')}ms)")
    except Exception as e:
        print(f"[Error] Cannot reach Argala node: {e}")
        sys.exit(1)

    # Step 1: Automatic
    build_staging_artifacts()

    # Step 2: Gated
    print("\n[Pipeline] Step 2: Preparing production deployment...")
    try:
        deploy_to_production("prod-us-east-cluster", release_tag="v2.4.0")
    except ArgalaApprovalDeniedError as e:
        print(f"\n[PIPELINE ABORTED] Deployment was REJECTED by operator: {e}")
    except ArgalaTimeoutError as e:
        print(f"\n[PIPELINE ABORTED] Timed out waiting for phone approval: {e}")


if __name__ == "__main__":
    main()
