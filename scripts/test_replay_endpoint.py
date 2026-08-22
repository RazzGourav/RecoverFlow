import asyncio
import httpx
import sys

async def main():
    async with httpx.AsyncClient() as client:
        # Get an OPEN case
        cases_res = await client.get("http://localhost:8000/cases/")
        if cases_res.status_code != 200:
            print("Failed to fetch cases")
            sys.exit(1)
            
        cases = cases_res.json()
        open_cases = [c for c in cases if c['status'] == 'OPEN']
        if not open_cases:
            print("No OPEN cases found")
            sys.exit(1)
            
        case_id = open_cases[0]['id']
        print(f"Testing replay for case {case_id}")
        
        replay_res = await client.post(
            f"http://localhost:8000/simulate/replay/{case_id}",
            json={"strategy": "RECOVERFLOW_OPTIMAL"}
        )
        
        if replay_res.status_code != 200:
            print(f"Replay failed: {replay_res.status_code}")
            print(replay_res.text)
            sys.exit(1)
            
        data = replay_res.json()
        print("Timeline events:", len(data['timeline']))
        print("Before action:", data['before']['action_type'])
        print("After action:", data['after']['action_type'])
        print("Before net:", data['before']['net_recovery_paise'])
        print("After net:", data['after']['net_recovery_paise'])
        print("SUCCESS")

if __name__ == "__main__":
    asyncio.run(main())
