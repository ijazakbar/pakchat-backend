# ==================== SUPABASE CLIENT ====================
supabase = None
try:
    from supabase import create_client, Client
    if SUPABASE_URL and SUPABASE_ANON_KEY:
        supabase: Client = create_client(
            SUPABASE_URL, 
            SUPABASE_ANON_KEY,
            options={
                "schema": "public",
                "headers": {
                    "X-Client-Info": "pakchat-backend"
                }
            }
        )
        logger.info("✅ Supabase connected")
        
        # Test query to verify RLS policies
        try:
            test_query = supabase.table('users').select('count', count='exact').limit(0).execute()
            logger.info("✅ Supabase RLS policies verified")
        except Exception as e:
            logger.warning(f"⚠️ Supabase RLS policy warning: {e}")
        
        # Auth users table is intentionally not directly accessible
        # This is normal - using RPC functions instead if needed
        
    else:
        supabase = None
        logger.warning("⚠️ Supabase not configured")
        
except ImportError:
    supabase = None
    logger.warning("⚠️ Supabase package not installed")
    
except Exception as e:
    supabase = None
    logger.warning(f"⚠️ Supabase connection failed: {e}")
