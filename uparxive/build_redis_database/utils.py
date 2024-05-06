import redis
def format_alias(alias_type, alias_value):
    return f"{alias_type}:{alias_value}"

def get_index_by_alias(r,alias_type, alias_value):
    unique_name = format_alias(alias_type, alias_value)
    # Get the index associated with the unique name
    return r.get(unique_name)

def get_alias_by_index(r,index):
    return r.smembers(f"index_{index}")
# Function to add an alias with a unique name to the Redis store

def add_alias_with_unique_name(r, alias_type, alias_value, index):
    unique_name = format_alias(alias_type, alias_value)
    # Set the unique name with the index
    #assert len(r.smembers(f"index_{index}"))==0, f'the index=[index_{index}] has already storage, please assign new index for alias_type={alias_type} and alias_value={alias_value}'
    r.set(unique_name, index) # assign the unique name with the index
    r.sadd(f"index_{index}", unique_name)



# Function to retrieve the index for a given unique name
def get_index_by_unique_name(r,alias_type, alias_value):
    unique_name = format_alias(alias_type, alias_value)
    # Get the index associated with the unique name
    return r.get(unique_name)