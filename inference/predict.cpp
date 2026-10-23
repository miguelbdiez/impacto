// Predicts the sentiment of reviews with a model trained in Neural Designer, using OpenNN.
//
// Usage: impacto_predict <model_dir> <sequence_length>
//
// <model_dir> holds model.json and model.bin (OpenNN formats) and vocabulary.txt (one token per
// line, the line number is the id), as written by training/export_model.py. The program reads one
// review per line from standard input, already normalised with impacto.text.normalize_text, and
// writes the probability of the positive class for each one, one per line, to standard output.

#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "opennn/core/configuration.h"
#include "opennn/network/network.h"
#include "opennn/network/operators/tokenizer_operator.h"

using namespace opennn;
using namespace std;

namespace
{

// Reviews are predicted in batches to bound memory: each one becomes a sequence_length x 64 matrix
constexpr Index batch_size = 1024;

vector<string> read_lines(istream& stream)
{
    vector<string> lines;
    for (string line; getline(stream, line);)
    {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        lines.push_back(move(line));
    }
    return lines;
}

// Reserved tokens ([PAD], [UNK], [START], [END]) open the vocabulary, written in brackets
vector<string> leading_reserved_tokens(const vector<string>& vocabulary)
{
    vector<string> reserved;
    for (const string& token : vocabulary)
    {
        if (token.size() < 3 || token.front() != '[' || token.back() != ']') break;
        reserved.push_back(token);
    }
    return reserved;
}

}

int main(int argc, char* argv[])
{
    try
    {
        if (argc != 3)
        {
            cerr << "Usage: impacto_predict <model_dir> <sequence_length>\n";
            return 2;
        }

        const filesystem::path model_dir = argv[1];
        const Index sequence_length = stoll(argv[2]);

        Configuration::instance().set(Device::CPU, Type::FP32);

        Network network(model_dir / "model.json");

        ifstream vocabulary_file(model_dir / "vocabulary.txt");
        const vector<string> vocabulary = read_lines(vocabulary_file);
        WordLevelTokenizer tokenizer(leading_reserved_tokens(vocabulary));
        tokenizer.set_vocabulary(vocabulary);

        const vector<string> reviews = read_lines(cin);
        cout.precision(9);

        for (Index first = 0; first < ssize(reviews); first += batch_size)
        {
            const Index rows = min(batch_size, ssize(reviews) - first);
            MatrixR inputs = MatrixR::Zero(rows, sequence_length);

            for (Index row = 0; row < rows; ++row)
            {
                // Same encoding as Neural Designer during training: [START] tokens [END], zero padding
                const vector<string> tokens = tokenizer.tokenize(reviews[size_t(first + row)]);
                const vector<Index> ids = tokenizer.encode_sequence(tokens, sequence_length);
                for (Index column = 0; column < ssize(ids); ++column)
                    inputs(row, column) = float(ids[size_t(column)]);
            }

            const MatrixR outputs = network.calculate_outputs(inputs);
            for (Index row = 0; row < rows; ++row)
                cout << outputs(row, 0) << '\n';
        }

        return 0;
    }
    catch (const exception& error)
    {
        cerr << error.what() << '\n';
        return 1;
    }
}
