#  Implement DNS-over-HTTPS (DoH) resolution in Python using the requests library.

import dns.resolver
import random
import time
from collections import defaultdict

class LoadBalancedDNSResolver:
    def __init__(self, servers, timeout=2, max_retries=2):
        """
        Initialize the load-balanced DNS resolver
        
        Args:
            servers: List of DNS server IPs
            timeout: Timeout for each DNS query in seconds
            max_retries: Maximum retries for failed queries
        """
        self.servers = servers
        self.timeout = timeout
        self.max_retries = max_retries
        self.failure_counts = defaultdict(int)
        self.success_counts = defaultdict(int)
    
    def resolve(self, domain, retry_count=0):
        """
        Resolve domain using random load balancing with fallback
        
        Args:
            domain: Domain name to resolve
            retry_count: Current retry attempt number
        """
        if retry_count >= self.max_retries:
            return {
                'success': False,
                'error': f"Failed to resolve {domain} after {self.max_retries} attempts"
            }
        
        # Randomly select a server
        server = random.choice(self.servers)
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [server]
        resolver.timeout = self.timeout
        resolver.lifetime = self.timeout
        
        try:
            start_time = time.time()
            
            # Use query for older versions, resolve for newer versions
            if hasattr(resolver, 'resolve'):
                answers = resolver.resolve(domain)
            else:
                answers = resolver.query(domain)
            
            response_time = time.time() - start_time
            self.success_counts[server] += 1
            
            return {
                'success': True,
                'server': server,
                'ip': answers[0].to_text(),
                'response_time': response_time,
                'domain': domain
            }
            
        except Exception as e:
            self.failure_counts[server] += 1
            # Retry with a different server
            return self.resolve(domain, retry_count + 1)
    
    def resolve_with_stats(self, domain):
        """Resolve and return detailed statistics"""
        result = self.resolve(domain)
        
        if result.get('success'):
            return (f"✅ Resolved by {result['server']} "
                   f"in {result['response_time']:.3f}s: "
                   f"{result['domain']} -> {result['ip']}")
        else:
            return f"❌ {result.get('error', 'Resolution failed')}"
    
    def get_stats(self):
        """Get statistics about server performance"""
        stats = {}
        for server in self.servers:
            stats[server] = {
                'successes': self.success_counts[server],
                'failures': self.failure_counts[server],
                'success_rate': 0
            }
            total = stats[server]['successes'] + stats[server]['failures']
            if total > 0:
                stats[server]['success_rate'] = (stats[server]['successes'] / total) * 100
        
        return stats
    
    def print_stats(self):
        """Print server statistics"""
        print("\n📊 DNS Server Statistics:")
        print("-" * 50)
        for server, stats in self.get_stats().items():
            print(f"Server {server}:")
            print(f"  ✅ Successes: {stats['successes']}")
            print(f"  ❌ Failures: {stats['failures']}")
            print(f"  📈 Success Rate: {stats['success_rate']:.1f}%")
        print("-" * 50)

# Weighted load balancer (some servers get more traffic)
class WeightedLoadBalancedDNSResolver(LoadBalancedDNSResolver):
    def __init__(self, servers_with_weights, timeout=2, max_retries=2):
        """
        Initialize weighted load balancer
        
        Args:
            servers_with_weights: List of tuples [(server_ip, weight), ...]
            timeout: Timeout for DNS queries
            max_retries: Maximum retries
        """
        self.servers = [server for server, weight in servers_with_weights]
        self.weights = [weight for server, weight in servers_with_weights]
        super().__init__(self.servers, timeout, max_retries)
    
    def resolve(self, domain, retry_count=0):
        """Resolve using weighted random selection"""
        if retry_count >= self.max_retries:
            return {
                'success': False,
                'error': f"Failed to resolve {domain} after {self.max_retries} attempts"
            }
        
        # Weighted random selection
        server = random.choices(self.servers, weights=self.weights, k=1)[0]
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [server]
        resolver.timeout = self.timeout
        resolver.lifetime = self.timeout
        
        try:
            start_time = time.time()  # Add timing
            
            if hasattr(resolver, 'resolve'):
                answers = resolver.resolve(domain)
            else:
                answers = resolver.query(domain)
            
            response_time = time.time() - start_time  # Calculate response time
            self.success_counts[server] += 1
            
            return {
                'success': True,
                'server': server,
                'ip': answers[0].to_text(),
                'response_time': response_time,  # Include response_time
                'domain': domain
            }
        except Exception as e:
            self.failure_counts[server] += 1
            return self.resolve(domain, retry_count + 1)

# DNS over HTTPS implementation
class DNSOverHTTPS:
    """DNS over HTTPS resolver"""
    def __init__(self):
        import urllib.request
        import json
        self.urllib = urllib.request
        self.json = json
    
    def resolve(self, domain, dns_server="https://cloudflare-dns.com/dns-query"):
        """
        Resolve domain using DNS over HTTPS
        
        Args:
            domain: Domain name to resolve
            dns_server: DoH server URL
        """
        import urllib.request
        import json
        
        url = f"{dns_server}?name={domain}&type=A"
        req = urllib.request.Request(url, headers={"Accept": "application/dns-json"})
        
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                
                if data.get("Answer"):
                    ips = [answer["data"] for answer in data["Answer"] if answer["type"] == 1]
                    return {
                        'success': True,
                        'ips': ips,
                        'server': dns_server
                    }
                else:
                    return {
                        'success': False,
                        'error': "No A records found"
                    }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

# Example usage and testing
if __name__ == "__main__":
    # Basic load balancer
    print("=== Basic Load Balancer ===")
    dns_servers = ["8.8.8.8", "1.1.1.1", "9.9.9.9"]
    resolver = LoadBalancedDNSResolver(dns_servers)
    
    # Test multiple resolutions
    for i in range(5):
        result = resolver.resolve_with_stats("example.com")
        print(result)
    
    # Print statistics
    resolver.print_stats()
    
    print("\n" + "="*50 + "\n")
    
    # Weighted load balancer (FIXED VERSION)
    print("=== Weighted Load Balancer ===")
    # Give more weight to Google DNS (8.8.8.8) and Cloudflare (1.1.1.1)
    weighted_servers = [
        ("8.8.8.8", 5),   # 50% weight
        ("1.1.1.1", 3),   # 30% weight
        ("9.9.9.9", 2)    # 20% weight
    ]
    
    weighted_resolver = WeightedLoadBalancedDNSResolver(weighted_servers)
    
    for i in range(10):
        result = weighted_resolver.resolve_with_stats("google.com")
        print(result)
    
    weighted_resolver.print_stats()
    
    print("\n" + "="*50 + "\n")
    
    # Test with different domains
    print("=== Testing Multiple Domains ===")
    domains = ["example.com", "google.com", "github.com", "stackoverflow.com"]
    
    for domain in domains:
        result = resolver.resolve_with_stats(domain)
        print(result)
    
    # DNS over HTTPS example
    print("\n" + "="*50 + "\n")
    print("=== DNS over HTTPS ===")
    doh = DNSOverHTTPS()
    result = doh.resolve("example.com")
    
    if result['success']:
        print(f"DoH Resolution successful:")
        print(f"   IPs: {', '.join(result['ips'])}")
        print(f"   Server: {result['server']}")
    else:
        print(f"DoH failed: {result['error']}")