#  Implement a Python script that queries multiple DNS servers in parallel and selects the fastest response.

import dns.resolver
import concurrent.futures
import time

def query_dns(server, domain, timeout=2):
    """Query DNS server and return response time and IP"""
    resolver = dns.resolver.Resolver()
    resolver.nameservers = [server]
    resolver.timeout = timeout
    resolver.lifetime = timeout
    
    start_time = time.time()
    try:
        # use query for older versions, resolve for newer versions
        if hasattr(resolver, 'resolve'):
            answers = resolver.resolve(domain)
        else:
            answers = resolver.query(domain)
        
        response_time = time.time() - start_time
        ip_address = answers[0].to_text()
        return server, response_time, ip_address, None
        
    except dns.resolver.NXDOMAIN:
        return server, None, None, "Domain does not exist"
    except dns.resolver.Timeout:
        return server, None, None, "Timeout"
    except Exception as e:
        return server, None, None, str(e)

def fastest_dns_response(domain, dns_servers, timeout=2):
    """Find the fastest DNS server for a given domain"""
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(dns_servers)) as executor:
        futures = [executor.submit(query_dns, server, domain, timeout) 
                  for server in dns_servers]
        
        results = []
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    
    # Filter out failed queries
    successful = [r for r in results if r[1] is not None]
    
    if not successful:
        print("All DNS servers failed to respond")
        return None
    
    fastest = min(successful, key=lambda x: x[1])
    return fastest

# Example usage
if __name__ == "__main__":
    domain = "example.com"
    dns_servers = ["8.8.8.8", "1.1.1.1", "9.9.9.9", "208.67.222.222"]  # Added OpenDNS
    
    print(f"Testing DNS servers for domain: {domain}\n")
    
    fastest = fastest_dns_response(domain, dns_servers)
    
    if fastest:
        print(f"Fastest DNS Server: {fastest[0]}")
        print(f"Response Time: {fastest[1]:.3f} seconds")
        print(f"IP Address: {fastest[2]}")
    else:
        print("No DNS servers responded successfully")