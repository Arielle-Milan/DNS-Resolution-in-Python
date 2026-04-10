# Implement a secure DNS resolution system that prevents cache poisoning using DNSSEC verification.  
import dns.resolver
import dns.dnssec
import dns.message
import dns.query
import dns.rdatatype
import dns.rdataset

def resolve_dns_with_dnssec(domain, dns_server="8.8.8.8"):
    """
    Resolve DNS with DNSSEC validation
    
    Args:
        domain: Domain name to resolve
        dns_server: DNS server to query (default: 8.8.8.8 - Google DNS)
    """
    try:
        print(f"\n--- DNSSEC Validation for {domain} ---")
        
        # Query for the DNSKEY record to fetch public keys
        dnskey_query = dns.message.make_query(domain, dns.rdatatype.DNSKEY, want_dnssec=True)
        response = dns.query.udp(dnskey_query, dns_server, timeout=5)
        
        # Extract DNSKEY and RRSIG records
        dnskey_rrset = None
        rrsig_rrset = None
        
        for rrset in response.answer:
            if rrset.rdtype == dns.rdatatype.DNSKEY:
                dnskey_rrset = rrset
                print(f"Found DNSKEY record for {domain}")
            elif rrset.rdtype == dns.rdatatype.RRSIG:
                rrsig_rrset = rrset
                print(f"Found RRSIG record for {domain}")
        
        # Check for DNSSEC records in authority section as well
        for rrset in response.authority:
            if rrset.rdtype == dns.rdatatype.DNSKEY:
                dnskey_rrset = rrset
            elif rrset.rdtype == dns.rdatatype.RRSIG:
                rrsig_rrset = rrset
        
        if not dnskey_rrset:
            print(f"DNSSEC verification failed: No DNSKEY records found for {domain}")
            print(f"   Note: Domain may not have DNSSEC enabled")
            return None
        
        if not rrsig_rrset:
            print(f"DNSSEC verification failed: No RRSIG records found for {domain}")
            return None
        
        # Verify the DNSSEC signature
        try:
            # Create a dictionary of DNSKEYs for validation
            keys = {domain: dnskey_rrset}
            dns.dnssec.validate(dnskey_rrset, rrsig_rrset, keys)
            print(f"DNSSEC verification successful for {domain}")
            
        except dns.dnssec.ValidationFailure as e:
            print(f"DNSSEC verification failed for {domain}: {e}")
            return None
        except Exception as e:
            print(f"DNSSEC validation error: {e}")
            return None
        
        # Resolve the domain normally after validation
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [dns_server]
        
        print(f"\n--- Resolving {domain} ---")
        answer = resolver.resolve(domain, "A")
        
        ip_addresses = []
        for ip in answer:
            ip_addresses.append(ip.to_text())
            print(f"{domain} resolves to {ip.to_text()}")
        
        return {
            "domain": domain,
            "dnssec_valid": True,
            "ip_addresses": ip_addresses,
            "dns_server": dns_server
        }
        
    except dns.exception.Timeout:
        print(f"Timeout: DNS server {dns_server} did not respond")
        return None
    except dns.resolver.NXDOMAIN:
        print(f"Domain {domain} does not exist")
        return None
    except dns.exception.DNSException as e:
        print(f"DNS resolution error: {e}")
        return None

def check_dnssec_for_multiple_domains(domains, dns_server="8.8.8.8"):
    """Check DNSSEC status for multiple domains"""
    results = []
    
    for domain in domains:
        result = resolve_dns_with_dnssec(domain, dns_server)
        if result:
            results.append(result)
        print("-" * 50)
    
    return results

# Example usage
if __name__ == "__main__":
    # Test with domains that have DNSSEC enabled
    domains_with_dnssec = [
        "example.com",      # Has DNSSEC
        "cloudflare.com",   # Has DNSSEC
        "google.com",       # Has DNSSEC
        "dnssec-failed.org" # Deliberately broken DNSSEC
    ]
    
    print("=== DNSSEC Validation Test ===\n")
    
    # Test single domain
    result = resolve_dns_with_dnssec("example.com", "8.8.8.8")
    
    print("\n" + "="*50 + "\n")
    
    # Test multiple domains
    print("Testing multiple domains:")
    results = check_dnssec_for_multiple_domains(domains_with_dnssec, "1.1.1.1")  # Using Cloudflare DNS
    
    # Summary
    print("\nSummary:")
    for result in results:
        print(f"{result['domain']}: DNSSEC Valid - IPs: {', '.join(result['ip_addresses'])}")