# Provide a Python script that implements DNS Query Caching with an Expiration Time for each cached DNS result.

import dns.resolver
import time
import threading
from datetime import datetime, timedelta
from collections import OrderedDict
import json
from typing import Dict, Optional, Tuple, Any

class DNSCacheEntry:
    """Represents a single DNS cache entry with expiration"""
    
    def __init__(self, domain: str, ip_addresses: list, ttl: int, record_type: str = "A"):
        """
        Initialize a DNS cache entry
        
        Args:
            domain: Domain name
            ip_addresses: List of IP addresses
            ttl: Time to live in seconds
            record_type: DNS record type (A, AAAA, etc.)
        """
        self.domain = domain
        self.ip_addresses = ip_addresses
        self.record_type = record_type
        self.created_at = time.time()
        self.expires_at = self.created_at + ttl
        self.ttl = ttl
        self.access_count = 0
        self.last_accessed = self.created_at
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired"""
        return time.time() > self.expires_at
    
    def get_remaining_ttl(self) -> float:
        """Get remaining TTL in seconds"""
        remaining = self.expires_at - time.time()
        return max(0, remaining)
    
    def access(self):
        """Record an access to this cache entry"""
        self.access_count += 1
        self.last_accessed = time.time()
    
    def to_dict(self) -> dict:
        """Convert cache entry to dictionary for serialization"""
        return {
            'domain': self.domain,
            'ip_addresses': self.ip_addresses,
            'record_type': self.record_type,
            'created_at': self.created_at,
            'expires_at': self.expires_at,
            'ttl': self.ttl,
            'access_count': self.access_count,
            'last_accessed': self.last_accessed
        }
    
    def __str__(self) -> str:
        return (f"DNSCacheEntry(domain={self.domain}, ips={self.ip_addresses}, "
                f"expires_in={self.get_remaining_ttl():.1f}s, accesses={self.access_count})")

class DNSCache:
    """DNS Cache Manager with LRU eviction and expiration"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300, cleanup_interval: int = 60):
        """
        Initialize the DNS cache
        
        Args:
            max_size: Maximum number of entries in cache
            default_ttl: Default TTL in seconds (5 minutes)
            cleanup_interval: Interval for automatic cleanup in seconds
        """
        self.cache: Dict[str, DNSCacheEntry] = OrderedDict()
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        self.hits = 0
        self.misses = 0
        self.lock = threading.Lock()
        
        # Start automatic cleanup thread
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Start background thread for periodic cache cleanup"""
        def cleanup_worker():
            while True:
                time.sleep(self.cleanup_interval)
                self.cleanup_expired()
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
    
    def _get_cache_key(self, domain: str, record_type: str = "A") -> str:
        """Generate cache key from domain and record type"""
        return f"{domain}:{record_type}"
    
    def get(self, domain: str, record_type: str = "A") -> Optional[DNSCacheEntry]:
        """
        Retrieve a cached DNS entry
        
        Args:
            domain: Domain name
            record_type: DNS record type
            
        Returns:
            Cache entry if found and not expired, None otherwise
        """
        key = self._get_cache_key(domain, record_type)
        
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                
                if not entry.is_expired():
                    entry.access()
                    self.hits += 1
                    # Move to end for LRU (most recently used)
                    self.cache.move_to_end(key)
                    return entry
                else:
                    # Remove expired entry
                    del self.cache[key]
            
            self.misses += 1
            return None
    
    def put(self, domain: str, ip_addresses: list, ttl: Optional[int] = None, 
            record_type: str = "A"):
        """
        Add a DNS entry to the cache
        
        Args:
            domain: Domain name
            ip_addresses: List of IP addresses
            ttl: Time to live (uses default if not provided)
            record_type: DNS record type
        """
        if ttl is None:
            ttl = self.default_ttl
        
        key = self._get_cache_key(domain, record_type)
        
        with self.lock:
            # Check if we need to evict entries
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict_lru()
            
            # Create and store cache entry
            entry = DNSCacheEntry(domain, ip_addresses, ttl, record_type)
            self.cache[key] = entry
            self.cache.move_to_end(key)
    
    def _evict_lru(self):
        """Evict the least recently used entry"""
        if self.cache:
            evicted_key, evicted_entry = self.cache.popitem(last=False)
            print(f"[Cache] Evicted LRU entry: {evicted_entry}")
    
    def cleanup_expired(self):
        """Remove all expired entries from cache"""
        with self.lock:
            expired_keys = [key for key, entry in self.cache.items() if entry.is_expired()]
            for key in expired_keys:
                del self.cache[key]
            
            if expired_keys:
                print(f"[Cache] Cleaned up {len(expired_keys)} expired entries")
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        with self.lock:
            total_queries = self.hits + self.misses
            hit_rate = (self.hits / total_queries * 100) if total_queries > 0 else 0
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': hit_rate,
                'total_queries': total_queries
            }
    
    def clear(self):
        """Clear all entries from cache"""
        with self.lock:
            self.cache.clear()
            print("[Cache] Cache cleared")
    
    def get_all_entries(self) -> list:
        """Get all cache entries (for debugging)"""
        with self.lock:
            return [entry.to_dict() for entry in self.cache.values()]
    
    def print_stats(self):
        """Print cache statistics"""
        stats = self.get_stats()
        print("\n" + "="*50)
        print("📊 DNS CACHE STATISTICS")
        print("="*50)
        print(f"Cache Size: {stats['size']}/{stats['max_size']}")
        print(f"Total Queries: {stats['total_queries']}")
        print(f"Cache Hits: {stats['hits']}")
        print(f"Cache Misses: {stats['misses']}")
        print(f"Hit Rate: {stats['hit_rate']:.1f}%")
        print("="*50)

class CachedDNSResolver:
    """DNS Resolver with caching support for video streaming"""
    
    def __init__(self, dns_servers: list = None, cache_max_size: int = 1000, 
                 cache_ttl: int = 300):
        """
        Initialize the cached DNS resolver
        
        Args:
            dns_servers: List of DNS servers to use
            cache_max_size: Maximum cache size
            cache_ttl: Default TTL for cache entries
        """
        self.dns_servers = dns_servers or ["8.8.8.8", "1.1.1.1"]
        self.cache = DNSCache(max_size=cache_max_size, default_ttl=cache_ttl)
        self.resolver = dns.resolver.Resolver()
        self.resolver.nameservers = self.dns_servers
        self.resolver.timeout = 2
        self.resolver.lifetime = 2
    
    def resolve(self, domain: str, record_type: str = "A", use_cache: bool = True) -> dict:
        """
        Resolve a domain name with caching
        
        Args:
            domain: Domain name to resolve
            record_type: DNS record type (A, AAAA, etc.)
            use_cache: Whether to use cache
            
        Returns:
            Dictionary with resolution results
        """
        # Check cache first
        if use_cache:
            cached_entry = self.cache.get(domain, record_type)
            if cached_entry:
                return {
                    'success': True,
                    'domain': domain,
                    'ip_addresses': cached_entry.ip_addresses,
                    'from_cache': True,
                    'remaining_ttl': cached_entry.get_remaining_ttl(),
                    'access_count': cached_entry.access_count
                }
        
        # Perform DNS query
        try:
            start_time = time.time()
            
            # Perform the DNS query
            if hasattr(self.resolver, 'resolve'):
                answers = self.resolver.resolve(domain, record_type)
            else:
                answers = self.resolver.query(domain, record_type)
            
            response_time = time.time() - start_time
            
            # Extract IP addresses
            ip_addresses = [answer.to_text() for answer in answers]
            
            # Get TTL from DNS response (if available)
            ttl = self._extract_ttl(answers)
            
            # Store in cache
            if use_cache:
                self.cache.put(domain, ip_addresses, ttl, record_type)
            
            return {
                'success': True,
                'domain': domain,
                'ip_addresses': ip_addresses,
                'from_cache': False,
                'response_time': response_time,
                'ttl': ttl,
                'dns_server': self.dns_servers[0]  # First server used
            }
            
        except dns.resolver.NXDOMAIN:
            return {
                'success': False,
                'domain': domain,
                'error': f"Domain '{domain}' does not exist"
            }
        except dns.resolver.NoAnswer:
            return {
                'success': False,
                'domain': domain,
                'error': f"No {record_type} records found for '{domain}'"
            }
        except dns.resolver.Timeout:
            return {
                'success': False,
                'domain': domain,
                'error': f"DNS query timed out for '{domain}'"
            }
        except Exception as e:
            return {
                'success': False,
                'domain': domain,
                'error': str(e)
            }
    
    def _extract_ttl(self, answers) -> int:
        """Extract TTL from DNS response"""
        try:
            # Try to get TTL from the first answer
            if hasattr(answers, 'rrset') and hasattr(answers.rrset, 'ttl'):
                return answers.rrset.ttl
            elif hasattr(answers, 'response') and answers.response.answer:
                for rrset in answers.response.answer:
                    if hasattr(rrset, 'ttl'):
                        return rrset.ttl
        except:
            pass
        return self.cache.default_ttl
    
    def resolve_multiple(self, domains: list, record_type: str = "A") -> dict:
        """Resolve multiple domains"""
        results = {}
        for domain in domains:
            results[domain] = self.resolve(domain, record_type)
        return results
    
    def preload_cache(self, domains: list, record_type: str = "A"):
        """Preload cache with common domains"""
        print(f"[Preload] Loading {len(domains)} domains into cache...")
        for domain in domains:
            self.resolve(domain, record_type)
        print(f"[Preload] Cache preloading complete")

class VideoStreamingDNSManager:
    """DNS Manager specifically for video streaming optimization"""
    
    def __init__(self):
        self.resolver = CachedDNSResolver(
            dns_servers=["8.8.8.8", "1.1.1.1", "9.9.9.9"],
            cache_max_size=500,
            cache_ttl=600  # 10 minutes for video content
        )
        
        # Common CDN domains for video streaming
        self.common_cdns = [
            "d1q6f0c8q5q5q5.cloudfront.net",
            "d2q6f0c8q5q5q5.cloudfront.net",
            "streaming.video-cdn.com",
            "content.video-platform.com"
        ]
    
    def get_video_server(self, video_id: str, region: str = "auto") -> dict:
        """
        Get optimal video server for streaming
        
        Args:
            video_id: Video identifier
            region: User region (auto, us, eu, asia)
        """
        # Construct CDN domain based on video ID and region
        if region != "auto":
            domain = f"{region}.cdn.video-platform.com"
        else:
            domain = f"global.cdn.video-platform.com"
        
        # Add video-specific path
        domain = f"{domain}/videos/{video_id}"
        
        # Resolve with caching
        result = self.resolver.resolve(domain)
        
        if result['success']:
            # Select best IP based on latency (simplified)
            best_ip = result['ip_addresses'][0] if result['ip_addresses'] else None
            
            return {
                'video_id': video_id,
                'server_ip': best_ip,
                'from_cache': result.get('from_cache', False),
                'available_ips': result['ip_addresses'],
                'cache_info': {
                    'remaining_ttl': result.get('remaining_ttl', 0),
                    'access_count': result.get('access_count', 0)
                }
            }
        else:
            return {
                'video_id': video_id,
                'error': result.get('error', 'Failed to resolve video server')
            }
    
    def optimize_for_streaming(self):
        """Preload cache for optimal streaming performance"""
        print("🎬 Optimizing DNS for video streaming...")
        
        # Preload common CDN domains
        self.resolver.preload_cache(self.common_cdns)
        
        # Preload popular video domains
        popular_videos = [f"video_{i}" for i in range(1, 11)]
        for video_id in popular_videos:
            self.get_video_server(video_id)
        
        print("✅ Streaming optimization complete")

# Demonstration and testing
def demo_dns_caching():
    """Demonstrate DNS caching functionality"""
    
    print("="*60)
    print("🎥 VIDEO STREAMING PLATFORM - DNS CACHING SYSTEM")
    print("="*60)
    
    # Initialize DNS manager
    dns_manager = VideoStreamingDNSManager()
    resolver = dns_manager.resolver
    
    # Test domain
    test_domain = "example.com"
    
    print(f"\n📡 Testing DNS resolution for: {test_domain}")
    print("-" * 40)
    
    # First query (cache miss)
    print("\n1️⃣ First query (should be cache miss):")
    result1 = resolver.resolve(test_domain)
    if result1['success']:
        print(f"   ✅ Resolved to: {', '.join(result1['ip_addresses'])}")
        print(f"   📍 From cache: {result1['from_cache']}")
        print(f"   ⏱️  Response time: {result1.get('response_time', 0):.3f}s")
    
    # Second query (should be cache hit)
    print("\n2️⃣ Second query (should be cache hit):")
    result2 = resolver.resolve(test_domain)
    if result2['success']:
        print(f"   ✅ Resolved to: {', '.join(result2['ip_addresses'])}")
        print(f"   📍 From cache: {result2['from_cache']}")
        print(f"   ⏳ Remaining TTL: {result2.get('remaining_ttl', 0):.1f}s")
        print(f"   🔢 Cache access count: {result2.get('access_count', 0)}")
    
    # Multiple domain resolution
    print("\n3️⃣ Resolving multiple domains:")
    domains = ["google.com", "github.com", "stackoverflow.com"]
    results = resolver.resolve_multiple(domains)
    for domain, result in results.items():
        if result['success']:
            cache_status = "CACHED" if result['from_cache'] else "FRESH"
            print(f"   {domain:20} -> {', '.join(result['ip_addresses'][:2])}... ({cache_status})")
    
    # Cache statistics
    resolver.cache.print_stats()
    
    # Video streaming optimization demo
    print("\n🎬 Video Streaming Optimization Demo:")
    print("-" * 40)
    
    # Get video server
    video_result = dns_manager.get_video_server("movie_12345", region="us")
    if 'server_ip' in video_result:
        print(f"   Video ID: {video_result['video_id']}")
        print(f"   Server IP: {video_result['server_ip']}")
        print(f"   From Cache: {video_result['from_cache']}")
        print(f"   Available IPs: {video_result['available_ips'][:3]}")
    
    # Get another video (should be faster due to cache)
    print("\n   Getting second video (cached):")
    video_result2 = dns_manager.get_video_server("movie_67890", region="eu")
    if 'server_ip' in video_result2:
        print(f"   Server IP: {video_result2['server_ip']}")
        print(f"   From Cache: {video_result2['from_cache']}")
    
    # Final statistics
    print("\n" + "="*60)
    print("FINAL CACHE PERFORMANCE")
    print("="*60)
    resolver.cache.print_stats()
    
    # Show cache entries
    print("\n📋 Current Cache Entries:")
    entries = resolver.cache.get_all_entries()
    for entry in entries[:5]:  # Show first 5 entries
        print(f"   {entry['domain']}: {', '.join(entry['ip_addresses'][:2])} "
              f"(expires in {entry['expires_at'] - time.time():.0f}s)")

if __name__ == "__main__":
    # Run the demo
    demo_dns_caching()
    
    # Additional test: Simulate video streaming session
    print("\n" + "="*60)
    print("🎬 SIMULATING VIDEO STREAMING SESSION")
    print("="*60)
    
    dns_manager = VideoStreamingDNSManager()
    
    # Simulate user watching multiple videos
    video_ids = ["movie_001", "series_002", "clip_003", "trailer_004"]
    
    for i, video_id in enumerate(video_ids, 1):
        print(f"\n🎥 Requesting video {i}: {video_id}")
        result = dns_manager.get_video_server(video_id)
        
        if 'server_ip' in result:
            cache_status = "⚡ CACHED" if result['from_cache'] else "🆕 FRESH"
            print(f"   Server: {result['server_ip']} ({cache_status})")
        else:
            print(f"   ❌ Error: {result.get('error')}")
        
        # Simulate some viewing time
        time.sleep(0.5)
    
    # Show final cache stats
    dns_manager.resolver.cache.print_stats()