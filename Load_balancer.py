#  Implement a load-balancing mechanism where DNS queries are distributed across multiple resolvers based on query load.

import dns.resolver  
import dns.query     
import dns.dnssec    

# function that performs a secure DNS query for the given domain
def secure_dns_query(domain):
    try:
        # create a DNS resolver instance
        resolver = dns.resolver.Resolver()
        
        # perform DNS resolution for the given domain
        answer = resolver.resolve(domain, raise_on_no_answer=True)
        
        print("DNS Query Results:")
        for rdata in answer:
            print(f"{rdata.to_text()}")  # Print each DNS record found
        
        # check if DNSSEC records are included in the additional section
        if answer.response.additional:
            print(f"DNSSEC records: {answer.response.additional}")
        else:  # Fixed: This else was incorrectly indented in your original
            print("No DNSSEC records found.")
        
        return answer
    except Exception as e:
        # handle exceptions and print the error message
        print(f"Error: {e}")
        return None

# example usage: Perform a secure DNS query for the given domain
domain = "www.google.com"
secure_dns_query(domain)