# PHP SDK

Native PHP client for Storage1024. Works with standard PHP 7.4+ and 8.0+.

### Requirements

Requires `php-curl` extension for file uploads.

### Setup

```php
require 'Storage1024.php';
use Storage1024\Storage1024;

$s1024 = new Storage1024();
$s1024->setUserID('YOUR_PROJECT_ID');
$s1024->setToken('YOUR_TOKEN');
```

### Global Variables

```php
// Read a variable
$val = $s1024->getGV('score');
echo "Score: " . $val;

// Write a variable
$s1024->addGV('score', '9001');
```

### File Upload

```php
$s1024->uploadFile('my_image', './photo.jpg');
```
