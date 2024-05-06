from flask import Flask, jsonify, request
import redis

app = Flask(__name__)
r = redis.StrictRedis(host='localhost', port=6379, db=0)

# @app.route('/set', methods=['POST'])
# def set_key():
#     key = request.json['key']
#     value = request.json['value']
#     r.set(key, value)
#     return jsonify(success=True)

@app.route('/get/<path:key>', methods=['GET'])
def get_key(key):
    if ":" in key:
        value = r.get(key)
        if value is not None:
            value = value.decode('utf-8')
        key = value
    
    value = " | ".join([t.decode('utf-8') for t in r.smembers(f"index_{key}")])
    
    return jsonify(value=value)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)