from inferencer import Inferencer
import segmentation_models_pytorch as smp
import torch
import pytorch_lightning as pl
# from model.create_model import ResUnetModel
import numpy as np
import cv2
import hashlib
import os

ALLOWED_ARCHS = {"Unet", "UnetPlusPlus", "FPN", "Linknet", "PSPNet", "PAN", "MAnet",
                 "DeepLabV3", "DeepLabV3Plus"}
# Only architecture options that cannot change channel/class counts or trigger downloads.
ALLOWED_EXTRA_KEYS = {"encoder_depth", "decoder_channels", "decoder_use_batchnorm",
                      "decoder_attention_type"}
MAX_PARAMETER_ELEMENTS = 200_000_000


MAX_CHECKPOINT_BYTES = int(os.environ.get("GAIA_MAX_CHECKPOINT_BYTES", 1024**3))


def _load_verified_checkpoint(path: str, expected_sha256) -> dict:
    """Load a checkpoint only if it is the exact file the configuration names.

    Fails closed: a model without a configured sha256 is refused. The digest
    is computed over the same open file that torch then reads, so the file
    cannot be swapped between the check and the load. Size is checked before
    any parsing."""
    if not expected_sha256:
        raise ValueError(
            "no sha256 configured for this checkpoint in parameters.json; "
            "refusing to load an unverified model")
    with open(path, "rb") as f:
        size = os.fstat(f.fileno()).st_size
        if size > MAX_CHECKPOINT_BYTES:
            raise ValueError(f"checkpoint is {size} bytes, the limit is {MAX_CHECKPOINT_BYTES}")
        h = hashlib.sha256()
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
        if h.hexdigest() != str(expected_sha256).strip().lower():
            raise ValueError("checkpoint digest does not match the configured sha256")
        f.seek(0)
        return torch.load(f, map_location='cpu', weights_only=True)


def validate_hyper_parameters(hp) -> dict:
    """Checkpoint metadata is untrusted: accept only a strict, bounded schema."""
    if not isinstance(hp, dict):
        raise ValueError("checkpoint hyper_parameters must be a mapping")
    allowed = {"arch", "encoder_name", "in_channels", "out_classes", "T_max"} | ALLOWED_EXTRA_KEYS
    unknown = set(hp) - allowed
    if unknown:
        raise ValueError(f"unsupported checkpoint hyper_parameters: {sorted(unknown)}")
    for key in ("arch", "encoder_name", "in_channels", "out_classes", "T_max"):
        if key not in hp:
            raise ValueError(f"checkpoint hyper_parameters is missing '{key}'")
    if hp["arch"] not in ALLOWED_ARCHS:
        raise ValueError("unsupported model architecture")
    name = hp["encoder_name"]
    if not (isinstance(name, str) and 0 < len(name) <= 64
            and all(c.isalnum() or c in "_-." for c in name)):
        raise ValueError("invalid encoder name")
    # the preprocessing buffers are fixed to 3 channels; this model is a single-class mask
    if hp["in_channels"] != 3 or hp["out_classes"] != 1:
        raise ValueError("only 3 input channels and 1 output class are supported")
    t_max = hp["T_max"]
    if isinstance(t_max, bool) or not isinstance(t_max, int) or not (0 < t_max <= 1_000_000):
        raise ValueError("invalid T_max")
    depth = hp.get("encoder_depth", 5)
    if isinstance(depth, bool) or not isinstance(depth, int) or not (1 <= depth <= 5):
        raise ValueError("invalid encoder_depth")
    channels = hp.get("decoder_channels")
    if channels is not None and not (
            isinstance(channels, (list, tuple)) and 0 < len(channels) <= 6
            and all(isinstance(c, int) and not isinstance(c, bool) and 0 < c <= 1024
                    for c in channels)):
        raise ValueError("invalid decoder_channels")
    return dict(hp)

class ResUnetModel(pl.LightningModule):
    def __init__(self, arch, encoder_name, in_channels, out_classes, T_max, **kwargs):
        super().__init__()
        self.save_hyperparameters()
        self.model = smp.create_model(
            arch,
            encoder_name=encoder_name,
            in_channels=in_channels,
            classes=out_classes,
            **kwargs,
        )

        # preprocessing parameteres for image (needed??)
        params = smp.encoders.get_preprocessing_params(encoder_name)
        self.register_buffer("std", torch.tensor(params["std"]).view(1, 3, 1, 1))
        self.register_buffer("mean", torch.tensor(params["mean"]).view(1, 3, 1, 1))

    def forward(self, image):
        # normalize image here
        image = (image - self.mean) / self.std
        mask = self.model(image)
        return mask

class ResUNetInferencer(Inferencer):
    """Performs inference on an image tile with the ResUNet model"""
    def __init__(self,checkpoint:str,**kwargs):
        """
        Parameters
        ----------
        checkpoint : str
            path to the model checkpoints to load
        resolution : float
            recommended resolution for the image in m/pixel, default is 0.05
        """
        ckpt = _load_verified_checkpoint(checkpoint, kwargs.pop('sha256', None))
        state_dict = ckpt['state_dict']
        total = 0
        for tensor in state_dict.values():
            total += tensor.numel()
            if total > MAX_PARAMETER_ELEMENTS:
                raise ValueError("checkpoint is larger than the allowed model size")
        hyper_parameters = validate_hyper_parameters(ckpt['hyper_parameters'])
        # never let a checkpoint trigger a pretrained-weights download
        self.model = ResUnetModel(**hyper_parameters, encoder_weights=None)
        self.model.load_state_dict(state_dict)

        self.params = {'resolution': 0.05}
        #updating parameters if specified in the call
        for key in kwargs:
            if not key in self.params:
                raise ValueError(f"{key} is not a valid argument")
            self.params[key] = kwargs[key]
    
    def predict(self, image: np.ndarray, image_resolution: float) -> np.ndarray:
        """Performs the inference of a given image
        Parameters
        ----------
        image : np.ndarray
            image to execute inference on
        image_resolution : float
            the image resolution in m/pixel

        Returns
        -------
        np.ndarray
            a grayscale image with probability that a pixel is foreground, values range between 0-255
        """
        #resize image
        resized_image = self.resizeImage(image,image_resolution)
        tensor = self.toTensor(resized_image)
        #run inference
        with torch.no_grad():
            self.model.eval()
            logits = self.model(tensor)
        pr_masks = logits.sigmoid()[0]
        prediction_image = pr_masks.numpy().squeeze()
        #resizing the output image to the same size as the input image
        (width,height) = (image.shape[1],image.shape[0])
        prediction_image = cv2.resize(prediction_image, (width,height),
                            interpolation=cv2.INTER_NEAREST)
        return np.uint8(255*prediction_image)
    
    def resizeImage(self, image: np.ndarray, image_resolution: float) -> np.ndarray:
        """Rescale image to a multiple of 32 pixels
        Parameters
        ----------
        image : np.ndarray
            image to resize
        image_resolution : float
            the resolution of the input image in m/pixel

        Returns
        -------
        np.ndarray
            resized image
        """
        return self.resizeImageToTargetResolution(image, image_resolution, self.params['resolution'],32)
    
    def toTensor(self,image:np.ndarray)->torch.tensor:
        """Converts image to a torch tensor that can be fed to the model

        Parameters
        ----------
        image : np.ndarray
            image to convert to tensor

        Returns
        -------
        torch.tensor
            the image converted to a torch tensor
        """
        imgChannelFirst = np.moveaxis(image, 2, 0)
        return torch.tensor(np.array([imgChannelFirst]))