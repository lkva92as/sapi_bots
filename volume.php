<?php

ignore_user_abort(true);

ob_end_clean();
ob_start();
echo('{"response_type": "in_channel", "text": "Checking, please wait..."}');
header($_SERVER["SERVER_PROTOCOL"] . " 200 OK");
header("Content-Type: application/json");
header('Content-Length: '.ob_get_length());
ob_end_flush();
ob_flush();
flush();

// usleep(100000);

$token = $_GET['token'];
$text = $_GET['text'];
$response_url = $_GET['response_url'];

ini_set('display_errors', 0);

if ($text == "rdts" || $text == "rdt") {
    $text = "realDonaldTrump";
}

$pi_json_file = file_get_contents('https://www.predictit.org/api/marketdata/all');
$pi_data = json_decode($pi_json_file, TRUE)['markets'];

$reply = "";


$markets = array();

foreach($pi_data as $key => $value) {
    if(stripos($value['name'].$value['shortName'], $text) !== false)
    {
        array_push($markets,$value);
        unset($pi_data[$key]);
    }
}

$contracts = array();

foreach($pi_data as $key => $value) {
    foreach ($value['contracts'] as $subkey => $subvalue) {
        if(stripos($subvalue['name'].$subvalue['shortName'],$text) !== false)
        {
            array_push($contracts, $value);
        }
    }
}

foreach($contracts as $key => $value) {
    foreach ($value['contracts'] as $subkey => $subvalue) {
        if(stripos($subvalue['name'].$subvalue['longName'].$subvalue['shortName'],$text) === false)
        {
            unset($contracts[$key]['contracts'][$subkey]);
        }
    }
    $contracts[$key]['contracts'] = array_values($contracts[$key]['contracts']);
}

$markets = array_merge($markets, $contracts);
$name_length = 3;
$total_length = 1;
$today_length = 1;


foreach($markets as $key => $value){
    $stats_url = "https://www.predictit.org/api/Market/".$value['id']."/Contracts/Stats";
    $stats_file = file_get_contents($stats_url);
    $stats_data = json_decode($stats_file, TRUE);
    foreach($stats_data as $stats_item) {
        foreach($value['contracts'] as $subkey => $subvalue) {
            if( strlen($subvalue['shortName']) > $name_length) {
                if ( $value['name'] !== $subvalue['name'] ){
                    $name_length = strlen($subvalue['shortName']);
                }
            }
            if($stats_item['contractId'] == $subvalue['id']) {
                $markets[$key]['contracts'][$subkey]['todaysVolume'] = $stats_item['todaysVolume'];
                if ( strlen(number_format($markets[$key]['contracts'][$subkey]['todaysVolume'])) > $today_length ) {
                    $today_length = strlen(number_format($markets[$key]['contracts'][$subkey]['todaysVolume']));
                }
                // $markets[$key]['contracts'][$subkey]['totalSharesTraded'] = $stats_item['totalSharesTraded'];
                $markets[$key]['contracts'][$subkey]['openInterest'] = $stats_item['openInterest'];
                if ( strlen(number_format($markets[$key]['contracts'][$subkey]['openInterest'])) > $total_length ) {
                    $total_length = strlen(number_format($markets[$key]['contracts'][$subkey]['openInterest']));
                }
            }
        }
    }
}


$reply = '';

foreach($markets as $key => $value) {
    // print($value['name']);
    $reply .= "<". $value['url'] . "|" . $value['name'] . ">\n";
    foreach($value['contracts'] as $subkey => $subvalue) {
        if ($subvalue['lastClosePrice'] > 0 ) {
            $subvalue['change'] = $subvalue['lastTradePrice'] - $subvalue['lastClosePrice'];
        }

        $reply.="`";
        if ($value['name'] !== $subvalue['name']) {
            $reply .= str_pad($subvalue['shortName'],$name_length);
        } else {
            $reply .= str_pad('Yes',$name_length);
        }

        $reply .= "  " . str_pad(100*$subvalue['lastTradePrice'],2," ", STR_PAD_LEFT) . "  ";

        if ( $subvalue['change'] > 0) {
            $reply.="↑".str_pad(100*$subvalue['change'],2);
        } elseif ( $subvalue['change'] < 0) {
            $reply.="↓".str_pad(-100*$subvalue['change'],2);
        } else {
            $reply.="---";
        }

        $reply .= "     Buy " . str_pad(100*$subvalue['bestBuyYesCost'],2," ", STR_PAD_LEFT) . "    "
        . "Sell " . str_pad(100*$subvalue['bestSellYesCost'],2," ", STR_PAD_LEFT) . "    "
        . "Shares " . str_pad(number_format($subvalue['openInterest']),$total_length," ", STR_PAD_LEFT) . "    "
        . "Today " . str_pad(number_format($subvalue['todaysVolume']),$today_length," ", STR_PAD_LEFT)
        . "`\n";
    }
    $reply .="\n";

}

if ($reply == "") {
    $reply = "`No Results`";
}

if ($token){
    $json = json_encode([
        "response_type"=>"in_channel",
        "text"=>$reply
    ]);

    $ch = curl_init();
    curl_setopt_array($ch, [
        CURLOPT_URL => $response_url,
        CURLOPT_POST => 1,
        CURLOPT_HTTPHEADER => ["Content-Type: application/json"],
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POSTFIELDS => $json
    ]);

    $resp = curl_exec($ch);
    curl_close($ch);
    error_log("API response: $resp");
} else {
    print($reply);
}



// print_r($markets);


?>
