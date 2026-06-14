"""
SentinelX — Flask Backend
API endpoint: POST /api/compile  { "source": "..." }
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import traceback
import os

from compiler.pipeline import compile_and_run

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)


@app.route('/')
def index():
    return send_from_directory('templates', 'index.html')


@app.route('/api/compile', methods=['POST'])
def compile_code():
    data = request.get_json(force=True)
    source = data.get('source', '')
    if not source.strip():
        return jsonify({"error": "Empty source code"}), 400
    try:
        result = compile_and_run(source)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "error": "Internal compiler error",
            "detail": str(e),
            "trace": traceback.format_exc()
        }), 500


@app.route('/api/sample/<name>')
def get_sample(name):
    samples = {
        "hello": """// Hello World in SentinelX
int x = 10;
int y = 20;
int sum = x + y;
print(sum);
""",
        "fibonacci": """// Fibonacci sequence
int a = 0;
int b = 1;
int i = 0;
while (i < 8) {
    print(a);
    int temp = a + b;
    a = b;
    b = temp;
    i = i + 1;
}
""",
        "conditions": """// If-else conditions
int score = 85;
if (score >= 90) {
    print("Grade: A");
} else {
    if (score >= 80) {
        print("Grade: B");
    } else {
        print("Grade: C");
    }
}
""",
        "optimization": """// Constant folding & propagation demo
int x = 3 + 4;
int y = x * 1;
int z = y + 0;
print(z);
""",
        "types": """// Type system demo
int count = 5;
float ratio = 3.14;
string name = "SentinelX";
bool flag = true;
print(count);
print(ratio);
print(name);
""",
        "errors": """// Error detection demo
int x = 10;
int x = 20;
string y = 42;
print(z);
"""
    }
    sample = samples.get(name)
    if not sample:
        return jsonify({"error": "Sample not found"}), 404
    return jsonify({"source": sample, "name": name})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
