<?php
ob_start();
ini_set('display_errors', 0);
require_once('common.php');
ini_set('display_errors', 0);
finishHim('data.txt',$arr);



echo "test";

ob_end_clean();
header('Content-Type: application/json');  // <-- header declaration
include('shortdata.json');

?>
