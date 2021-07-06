import numpy as np
from onnx import load
from onnx.onnx_ONNX_REL_1_7_ml_pb2 import ModelProto
from onnxruntime.backend import prepare


def run_model(data: bytearray, model: ModelProto):
    """Run model and check result"""

    x = np.array(data, dtype=np.int64)
    i = np.array([0], dtype=np.int64)
    keep_going = np.array([True], dtype=np.bool)
    max_index = np.array([32], dtype=np.int64)
    model_rep = prepare(model)
    out = model_rep.run([x, i, keep_going, max_index])[1].reshape((1, 30))[0]
    assert np.array_equal(
        out,
        np.array(
            [
                16780,
                9831,
                2538,
                14031,
                8110,
                19136,
                17547,
                13929,
                16911,
                20265,
                15014,
                24203,
                9238,
                12759,
                17883,
                5871,
                15265,
                13222,
                11014,
                8290,
                7843,
                16989,
                7222,
                20835,
                15431,
                4554,
                8498,
                11543,
                6214,
                7169,
            ],
            dtype=np.int64,
        ),
    )
    print(f"Flag: ctfzone\x7b{data.decode()}\x7d")


if __name__ == "__main__":
    data = input("Enter your password 32 bytes long: ")
    if len(data) != 32:
        exit("Invalid length")
    model = load("model.onnx")
    try:
        run_model(bytearray(data.encode()), model)
    except AssertionError:
        print("Wrong password")
