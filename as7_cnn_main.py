import tensorflow as tf
import matplotlib.pyplot as plt
import numpy as np
import six.moves.cPickle as pickle
import time

def accuracy(predictions, labels):
    return (100.0 * np.sum(np.argmax(predictions, 1) == np.argmax(labels, 1))
        / predictions.shape[0])


if __name__ == '__main__':

    model_type = 2

    pickle_file = 'notMNIST.pickle'

    with open(pickle_file, 'rb') as f:
        save = pickle.load(f)
        train_dataset = save['train_dataset']
        train_labels = save['train_labels']
        valid_dataset = save['valid_dataset']
        valid_labels = save['valid_labels']
        test_dataset = save['test_dataset']
        test_labels = save['test_labels']
        del save  # hint to help gc free up memory
        print('Training set', train_dataset.shape, train_labels.shape)
        print('Validation set', valid_dataset.shape, valid_labels.shape)
        print('Test set', test_dataset.shape, test_labels.shape)


    image_size = 28
    num_labels = 10
    num_channels = 1 # grayscale

    def reformat(dataset, labels):
        dataset = dataset.reshape(
        (-1, image_size, image_size, num_channels)).astype(np.float32)
        labels = (np.arange(num_labels) == labels[:,None]).astype(np.float32)
        return dataset, labels
    train_dataset, train_labels = reformat(train_dataset, train_labels)
    valid_dataset, valid_labels = reformat(valid_dataset, valid_labels)
    test_dataset, test_labels = reformat(test_dataset, test_labels)
    print('Training set', train_dataset.shape, train_labels.shape)
    print('Validation set', valid_dataset.shape, valid_labels.shape)
    print('Test set', test_dataset.shape, test_labels.shape)

    batch_size = 16
    patch_size = 5
    depth = 16
    num_hidden = 64

    graph = tf.Graph()

    with graph.as_default():

        # Input data.
        tf_train_dataset = tf.placeholder(
        tf.float32, shape=(batch_size, image_size, image_size, num_channels))
        tf_train_labels = tf.placeholder(tf.float32, shape=(batch_size, num_labels))
        tf_valid_dataset = tf.constant(valid_dataset)
        tf_test_dataset = tf.constant(test_dataset)

        # Variables.
        layer1_weights = tf.Variable(tf.truncated_normal(
          [patch_size, patch_size, num_channels, depth], stddev=0.1))
        layer1_biases = tf.Variable(tf.zeros([depth]))
        layer2_weights = tf.Variable(tf.truncated_normal(
          [patch_size, patch_size, depth, depth*2], stddev=0.1))
        layer2_biases = tf.Variable(tf.constant(1.0, shape=[depth*2]))
        layer3_weights = tf.Variable(tf.truncated_normal(
          [image_size // 4 * image_size // 4 * (depth*2), num_hidden], stddev=0.1))
        layer3_biases = tf.Variable(tf.constant(1.0, shape=[num_hidden]))
        layer4_weights = tf.Variable(tf.truncated_normal(
          [num_hidden, num_labels], stddev=0.1))
        layer4_biases = tf.Variable(tf.constant(1.0, shape=[num_labels]))

        # Model.
        def model(data, type):
            if type == 1:
                return model_maxpool(data)
            elif type == 2:
                return model_maxpool_lrn(data)
            else:
                return model_original(data)


        # Model.-------------oringinal
        def model_original(data):
            conv = tf.nn.conv2d(data, layer1_weights, [1, 2, 2, 1], padding='SAME')
            hidden = tf.nn.relu(conv + layer1_biases)
            conv = tf.nn.conv2d(hidden, layer2_weights, [1, 2, 2, 1], padding='SAME')
            hidden = tf.nn.relu(conv + layer2_biases)
            shape = hidden.get_shape().as_list()
            reshape = tf.reshape(hidden, [shape[0], shape[1] * shape[2] * shape[3]])
            hidden = tf.nn.relu(tf.matmul(reshape, layer3_weights) + layer3_biases)
            return tf.matmul(hidden, layer4_weights) + layer4_biases

        def model_maxpool(data):
            conv = tf.nn.conv2d(data, layer1_weights, [1, 1, 1, 1], padding='SAME')
            hidden = tf.nn.relu(conv + layer1_biases)
            maxpool = tf.nn.max_pool(hidden, [1, 2, 2, 1], [1, 2, 2, 1], padding='SAME')

            conv = tf.nn.conv2d(maxpool, layer2_weights, [1, 1, 1, 1], padding='SAME')
            hidden = tf.nn.relu(conv + layer2_biases)
            maxpool = tf.nn.max_pool(hidden, [1, 2, 2, 1], [1, 2, 2, 1], padding='SAME')

            shape = maxpool.get_shape().as_list()
            reshape = tf.reshape(maxpool, [shape[0], shape[1] * shape[2] * shape[3]])
            hidden = tf.nn.relu(tf.matmul(reshape, layer3_weights) + layer3_biases)
            return tf.matmul(hidden, layer4_weights) + layer4_biases

        def model_maxpool_lrn(data):# with local respond normalization
            conv = tf.nn.conv2d(data, layer1_weights, [1, 1, 1, 1], padding='SAME')
            hidden = tf.nn.relu(conv + layer1_biases)
            hidden = tf.nn.dropout(hidden, 0.5)
            lrn_b = tf.nn.local_response_normalization(hidden,bias=2, alpha=0.0001, beta=0.75)
            maxpool = tf.nn.max_pool(lrn_b, [1, 2, 2, 1], [1, 2, 2, 1], padding='SAME')

            conv = tf.nn.conv2d(maxpool, layer2_weights, [1, 1, 1, 1], padding='SAME')
            hidden = tf.nn.relu(conv + layer2_biases)
            #hidden = tf.nn.dropout(hidden, 0.5)
            lrn_b = tf.nn.local_response_normalization(hidden,bias=2, alpha=0.0001, beta=0.75)
            maxpool = tf.nn.max_pool(lrn_b, [1, 2, 2, 1], [1, 2, 2, 1], padding='SAME')

            shape = maxpool.get_shape().as_list()
            reshape = tf.reshape(maxpool, [shape[0], shape[1] * shape[2] * shape[3]])
            hidden = tf.nn.relu(tf.matmul(reshape, layer3_weights) + layer3_biases)
            #hidden = tf.nn.dropout(hidden, 0.5)
            return tf.matmul(hidden, layer4_weights) + layer4_biases

        # Training computation.
        #logits = model(tf_train_dataset)
        logits = model(tf_train_dataset, model_type)
        loss = tf.reduce_mean(
        tf.nn.softmax_cross_entropy_with_logits(logits, tf_train_labels))

        # Optimizer.
        global_step = tf.Variable(10001, trainable=False)
        starter_learning_rate = 0.05
        learning_rate = tf.train.exponential_decay(starter_learning_rate, global_step,400, 0.99, staircase=True)
        optimizer = tf.train.GradientDescentOptimizer(learning_rate).minimize(loss)

        # Predictions for the training, validation, and test data.
        train_prediction = tf.nn.softmax(logits)
        #valid_prediction = tf.nn.softmax(model(tf_valid_dataset))
        valid_prediction = tf.nn.softmax(model(tf_valid_dataset,model_type))
        test_prediction = tf.nn.softmax(model(tf_test_dataset, model_type))
        #test_prediction = tf.nn.softmax(model(tf_test_dataset))

    #graph = build_graph(batch_size, patch_size, depth, num_hidden)

    num_steps = 10001

    with tf.Session(graph=graph) as session:
        tf.initialize_all_variables().run()
        print('Initialized')
        starttime = time.clock()
        print('start time = ', starttime)
        
        for step in range(num_steps):
            offset = (step * batch_size) % (train_labels.shape[0] - batch_size)

            batch_data = train_dataset[offset:(offset + batch_size), :, :, :]
            batch_labels = train_labels[offset:(offset + batch_size), :]
            feed_dict = {tf_train_dataset : batch_data, tf_train_labels : batch_labels}

            _,k, l, predictions = session.run(
              [optimizer,learning_rate,loss, train_prediction], feed_dict=feed_dict)

            if (step % 50 == 0):
                print('\nOffset = ' + str(offset))
                print('Minibatch loss at step %d: %f' % (step, l))
                print('learning_rate\t',k)
                print('Minibatch accuracy: %.1f%%' % accuracy(predictions, batch_labels))
                print('Validation accuracy: %.1f%%' % accuracy(
                valid_prediction.eval(), valid_labels))
                print('current time passed = ', time.clock() - starttime)
        
        print('Test accuracy: %.1f%%' % accuracy(test_prediction.eval(), test_labels))
        print('end time = ', time.clock())
        print('total time = ', time.clock() - starttime)

    i = tf.constant('finished')
    print(i)
