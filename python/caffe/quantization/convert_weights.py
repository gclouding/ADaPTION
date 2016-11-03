'''
This script converts weights, which are trained without rounding, to match the size of the
data blobs of low precison rounded weights.
In high precision each conv layer has two blob allocated for the weights and the biases
However in low precision, since we are using dual copy roudning/pow2quantization, we basically
have 4 blobs weights in high and low precision and biases in high and low precision

Input:
    net_name: Name of the network you want to convert. This name can be arbitraly set as long as 

Output:

Author: Moritz Milde
Date: 02.11.2016
E-Mail: mmilde@ini.uzh.ch

'''
import numpy as np
import caffe
import os


class convert_weights():
    def __init__(self):
        self.caffe_root = '/home/moritz/Repositories/caffe_lp/'
        self.model_dir = 'examples/low_precision/imagenet/models/'
        self.weight_dir = '/media/moritz/Data/ILSVRC2015/pre_trained/'
        self.save_name = 'HP_VGG16_v2.caffemodel'

    def download_model(self, net_name, current_dir):
        if not os.path.exists(current_dir):
            print 'Create working direcory'
            os.makedirs(current_dir)
        if net_name == 'VGG16':
            print 'Downloading to ' + current_dir
            filename = '%s.caffemodel' % (net_name + '_original')
            if not os.path.isfile(current_dir + filename):
                url = 'http://www.robots.ox.ac.uk/%7Evgg/software/very_deep/caffe/VGG_ILSVRC_16_layers.caffemodel'
                os.system('wget -O %s %s' % (current_dir + filename, url))
                print 'Done'
            else:
                print 'File already downloaded'
            return True
        else:
            print 'Please download disired files from https://github.com/BVLC/caffe/wiki/Model-Zoo'
            return False

    def convert_weights(self, net_name, save_name=None, caffe_root=None, model_dir=None, weight_dir=None, debug=False):
        if caffe_root is not None:
            self.caffe_root = caffe_root
        if model_dir is not None:
            self.model_dir = model_dir
        if weight_dir is not None:
            self.weight_dir = weight_dir

        vgg_original = 'VGG16_original.caffemodel'
        vgg_new = 'HP_VGG16.caffemodel'
        current_dir = weight_dir + net_name + '/'
        flag = convert_weights.download_model(self, net_name, current_dir)
        assert flag, 'Please download caffemodel manually. This type of network currently not supported for automatized download.'

        if debug:
            print 'Copying {} to {}'.format(vgg_original, vgg_new)
            print current_dir
        os.system('cp %s %s' % (current_dir + vgg_original, current_dir + vgg_new))
        weights_hp = current_dir + vgg_new
        weights_lp = current_dir + 'dummyLP.caffemodel.h5'

        prototxt_hp = self.caffe_root + self.model_dir + 'VGG16_deploy.prototxt'
        prototxt_lp = self.caffe_root + self.model_dir + 'dummyLP_deploy.prototxt'

        caffe.set_mode_gpu()
        caffe.set_device(0)
        net_hp = caffe.Net(prototxt_hp, weights_hp, caffe.TEST)
        if debug:
            print('Doing forward pass for original high precision network')
        net_hp.forward()
        if debug:
            print('Done.')

        caffe.set_mode_gpu()
        caffe.set_device(0)
        net_lp = caffe.Net(prototxt_lp, weights_lp, caffe.TEST)
        print('Doing forward pass for low precision network')
        net_lp.forward()
        print('Done.')

        sparsity_hp = open(self.weight_dir + 'sparsity_hp.txt', 'w')
        sparsity_lp = open(self.weight_dir + 'sparsity_lp.txt', 'w')
        for i, ldx in enumerate(net_hp.params.keys()):
            ldx_lp = net_lp.params.keys()[i]
            W = net_hp.params[ldx][0].data[...]
            b = net_hp.params[ldx][1].data[...]
            # Calculate sparsity for each layer
            W_reshape = np.reshape(W, [1, -1])
            sparsity1 = float(np.sum(W_reshape[0, :] == 0)) / float(len(W_reshape[0, :])) * 100.
            sparsity_hp.write('%s layer: %f \n' % (ldx, sparsity1))

            W_reshape = np.reshape(net_lp.params[ldx_lp][1].data[...], [1, -1])
            sparsity2 = float(np.sum(W_reshape[0, :] == 0)) / float(len(W_reshape[0, :])) * 100.
            sparsity_lp.write('%s layer: %f \n' % (ldx_lp, sparsity2))
            net_lp.params[ldx_lp][0].data[...] = W
            net_lp.params[ldx_lp][1].data[...] = W
            net_lp.params[ldx_lp][2].data[...] = b
            net_lp.params[ldx_lp][3].data[...] = b
        if save_name is not None:
            self.save_name = '{}.caffemodel'.format(save_name)
        net_lp.save(current_dir + self.save_name)
        sparsity_hp.close()
        sparsity_lp.close()
        print 'Saving done caffemodel to {}'.format(current_dir + self.save_name)
